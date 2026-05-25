from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, Mapping, Optional

from fixed_income.data._env import load_project_dotenv
from fixed_income.data.base import DataSource, parse_date, require_requests
from fixed_income.data.types import RateObservation, RateSeries

_dotenv_loaded = False


def _ensure_dotenv() -> None:
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_project_dotenv()
        _dotenv_loaded = True


class FredSeriesSource(DataSource):
    """Minimal FRED API client for a single series."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, series_id: str, api_key: Optional[str] = None, timeout_s: float = 30.0):
        _ensure_dotenv()
        self.series_id = series_id
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        self.timeout_s = float(timeout_s)

    @property
    def name(self) -> str:
        return f"fred:{self.series_id}"

    def _fetch_observations(
        self,
        as_of: Optional[date] = None,
        start_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        if not self.api_key:
            raise ValueError("Missing FRED API key; set FRED_API_KEY or pass api_key=...")

        requests = require_requests()
        params: Dict[str, Any] = {
            "series_id": self.series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "asc",
        }
        if start_date is not None:
            params["observation_start"] = start_date.isoformat()
        if as_of is not None:
            params["observation_end"] = as_of.isoformat()

        resp = requests.get(self.BASE_URL, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        return list(payload.get("observations") or [])

    def fetch(self, as_of: Optional[date] = None) -> Mapping[str, Any]:
        obs = self._fetch_observations(as_of=as_of)
        if not obs:
            raise RuntimeError(f"No observations returned for series {self.series_id!r}.")

        last = None
        for o in reversed(obs):
            v = o.get("value")
            if v not in (None, ".", ""):
                last = o
                break
        if last is None:
            raise RuntimeError(f"All observations are missing for series {self.series_id!r}.")

        return {
            "series_id": self.series_id,
            "as_of": parse_date(last["date"]),
            "value": float(last["value"]),
        }

    def fetch_history(
        self,
        as_of: Optional[date] = None,
        *,
        start_date: Optional[date] = None,
        lookback_days: Optional[int] = None,
    ) -> RateSeries:
        target = as_of or date.today()
        if start_date is None:
            if lookback_days is None:
                lookback_days = 365
            start_date = target - timedelta(days=int(lookback_days))

        obs = self._fetch_observations(as_of=target, start_date=start_date)
        points: list[RateObservation] = []
        for o in obs:
            v = o.get("value")
            if v in (None, ".", ""):
                continue
            dt = parse_date(o["date"])
            if dt > target:
                continue
            # FRED SOFR is percent; index is index level — store as returned, document in wrappers
            points.append(RateObservation(date=dt, rate=float(v)))

        if not points:
            raise RuntimeError(f"No valid observations for series {self.series_id!r}.")

        effective = points[-1].date
        return RateSeries(series_id=self.series_id, as_of=effective, observations=tuple(points))


class FredCorporateSpreadsSource(FredSeriesSource):
    """Corporate OAS from FRED (default ICE BofA US Corporate OAS)."""

    def __init__(self, series_id: str = "BAMLC0A0CM", api_key: Optional[str] = None, timeout_s: float = 30.0):
        super().__init__(series_id=series_id, api_key=api_key, timeout_s=timeout_s)

    def fetch_spread_bps(self, as_of: Optional[date] = None) -> Mapping[str, Any]:
        data = dict(self.fetch(as_of=as_of))
        data["spread_bps"] = float(data["value"]) * 100.0
        return data


class FredSofrSource(FredSeriesSource):
    """Overnight SOFR (percent in FRED; use ``fetch_history`` and divide by 100 for decimal)."""

    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 30.0):
        super().__init__(series_id="SOFR", api_key=api_key, timeout_s=timeout_s)

    def fetch_history(
        self,
        as_of: Optional[date] = None,
        *,
        start_date: Optional[date] = None,
        lookback_days: Optional[int] = None,
    ) -> RateSeries:
        series = super().fetch_history(
            as_of=as_of, start_date=start_date, lookback_days=lookback_days
        )
        obs = tuple(RateObservation(date=o.date, rate=o.rate / 100.0) for o in series.observations)
        return RateSeries(series_id=self.series_id, as_of=series.as_of, observations=obs)


class FredSofrIndexSource(FredSeriesSource):
    """SOFR Index (FRED SOFRINDEX)."""

    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 30.0):
        super().__init__(series_id="SOFRINDEX", api_key=api_key, timeout_s=timeout_s)


class FredSofr30DayAvgSource(FredSeriesSource):
    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 30.0):
        super().__init__(series_id="SOFR30DAYAVG", api_key=api_key, timeout_s=timeout_s)
