from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fixed_income.data import (
    CachedDataSource,
    CmeSofrSettleBundleSource,
    CmeSofrSettleCsvSource,
    FredSeriesSource,
    FredSofrSource,
    NyFedSofrSource,
    RateSeries,
    month_label_to_symbol,
    parse_cme_price,
    parse_settle_csv,
)
from fixed_income.data.base import DataSource

FIXTURES = Path(__file__).parent / "fixtures"
TRADE_DATE = date(2026, 5, 22)


def test_parse_cme_price_strips_suffix():
    assert parse_cme_price("95.9900B") == 95.99
    assert parse_cme_price("-") is None


def test_month_label_to_symbol():
    assert month_label_to_symbol("SR1", "MAY 26") == "SR1K6"
    assert month_label_to_symbol("SR3", "JUN 26") == "SR3M6"


def test_parse_settle_csv_sample():
    curve = parse_settle_csv(FIXTURES / "cme_1m_settle_sample.csv", "SR1", TRADE_DATE)
    assert curve.as_of == TRADE_DATE
    assert curve.product == "SR1"
    assert len(curve.settles) == 3
    assert curve.settles[0].settle == pytest.approx(96.4175)
    assert curve.settles[2].symbol == "SR1J7"


def test_cme_settle_wrong_as_of_raises():
    src = CmeSofrSettleCsvSource(FIXTURES / "cme_1m_settle_sample.csv", "SR1", TRADE_DATE)
    with pytest.raises(ValueError, match="only has data"):
        src.fetch(as_of=date(2026, 1, 1))


def test_cme_bundle_from_samples():
    bundle = CmeSofrSettleBundleSource(
        trade_date=TRADE_DATE,
        path_1m=FIXTURES / "cme_1m_settle_sample.csv",
        path_3m=FIXTURES / "cme_1m_settle_sample.csv",
    ).fetch(as_of=TRADE_DATE)
    assert bundle.sr1.product == "SR1"
    assert bundle.sr3.product == "SR3"


@patch("fixed_income.data.nyfed.require_requests")
def test_nyfed_sofr_parse(mock_req):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json.loads((FIXTURES / "nyfed_sofr.json").read_text())
    mock_resp.raise_for_status = MagicMock()
    mock_req.return_value.get.return_value = mock_resp

    series = NyFedSofrSource(default_lookback_days=30).fetch(as_of=date(2026, 5, 22))
    assert isinstance(series, RateSeries)
    assert series.observations[-1].rate == pytest.approx(0.0351)
    assert series.observations[-1].date == date(2026, 5, 21)


@patch("fixed_income.data.fred.require_requests")
def test_fred_fetch_history(mock_req):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json.loads((FIXTURES / "fred_observations.json").read_text())
    mock_resp.raise_for_status = MagicMock()
    mock_req.return_value.get.return_value = mock_resp

    with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
        series = FredSofrSource(api_key="test-key").fetch_history(
            as_of=date(2026, 5, 22), lookback_days=30
        )
    assert len(series.observations) == 2
    assert series.observations[-1].rate == pytest.approx(0.0433)


@patch("fixed_income.data.fred.require_requests")
def test_fred_fetch_latest_dict(mock_req):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json.loads((FIXTURES / "fred_observations.json").read_text())
    mock_resp.raise_for_status = MagicMock()
    mock_req.return_value.get.return_value = mock_resp

    out = FredSeriesSource("SOFR", api_key="test-key").fetch(as_of=date(2026, 5, 22))
    assert out["value"] == pytest.approx(4.33)


def test_cached_data_source_roundtrip(tmp_path):
    class _FixedSource(DataSource):
        @property
        def name(self) -> str:
            return "test:fixed"

        def fetch(self, as_of=None):
            from fixed_income.data.types import CurvePoint, ParCurve

            return ParCurve(
                as_of=date(2026, 5, 22),
                points=(CurvePoint(maturity_years=1.0, par_yield=0.04),),
            )

    cached = CachedDataSource(_FixedSource(), cache_dir=tmp_path, max_age_hours=999)
    first = cached.fetch()
    second = cached.fetch()
    assert first.as_of == second.as_of
    assert first.points[0].par_yield == second.points[0].par_yield
