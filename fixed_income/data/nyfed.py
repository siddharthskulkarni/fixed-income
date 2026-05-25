from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from fixed_income.data.base import DataSource, parse_date, require_requests
from fixed_income.data.types import RateObservation, RateSeries

NY_FED_BASE = "https://markets.newyorkfed.org/api"


class NyFedSofrSource(DataSource):
    """Secured overnight SOFR fixings from the NY Fed Markets API (rates in percent → decimal)."""

    def __init__(self, timeout_s: float = 30.0, default_lookback_days: int = 365):
        self.timeout_s = float(timeout_s)
        self.default_lookback_days = int(default_lookback_days)

    @property
    def name(self) -> str:
        return "nyfed:sofr"

    def _get_json(self, path: str, params: Optional[dict[str, str]] = None) -> dict[str, Any]:
        requests = require_requests()
        url = f"{NY_FED_BASE}{path}"
        resp = requests.get(url, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def fetch(self, as_of: Optional[date] = None) -> RateSeries:
        target = as_of or date.today()
        start = target - timedelta(days=self.default_lookback_days)
        payload = self._get_json(
            "/rates/secured/sofr/search.json",
            {"startDate": start.isoformat(), "endDate": target.isoformat()},
        )
        ref_rates = payload.get("refRates") or []
        points: list[RateObservation] = []
        for row in ref_rates:
            if row.get("type") != "SOFR":
                continue
            dt = parse_date(row["effectiveDate"])
            if dt > target:
                continue
            pct = float(row["percentRate"])
            points.append(RateObservation(date=dt, rate=pct / 100.0))

        if not points:
            raise RuntimeError(f"No NY Fed SOFR data through {target.isoformat()}.")

        points.sort(key=lambda o: o.date)
        # Weekend/holiday: last available <= target
        effective = points[-1].date
        return RateSeries(series_id="SOFR", as_of=effective, observations=tuple(points))
