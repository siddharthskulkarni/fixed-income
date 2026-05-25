from __future__ import annotations

import csv
import io
from datetime import date
from typing import Dict, List, Mapping, Optional, Sequence

from fixed_income.data.base import DataSource, parse_date, require_requests
from fixed_income.data.types import CurvePoint, ParCurve


class TreasuryParCurveSource(DataSource):
    """
    Daily US Treasury par yield curve from Treasury.gov CSV.

    Notes:
    - The Treasury dataset is par yields (not zero rates).
    - Yields are returned in decimal form.
    """

    DEFAULT_URL_TEMPLATE = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}"
    )

    _TENOR_TO_YEARS: Mapping[str, float] = {
        "1 Mo": 1.0 / 12.0,
        "2 Mo": 2.0 / 12.0,
        "3 Mo": 3.0 / 12.0,
        "4 Mo": 4.0 / 12.0,
        "6 Mo": 0.5,
        "1 Yr": 1.0,
        "2 Yr": 2.0,
        "3 Yr": 3.0,
        "5 Yr": 5.0,
        "7 Yr": 7.0,
        "10 Yr": 10.0,
        "20 Yr": 20.0,
        "30 Yr": 30.0,
    }

    def __init__(
        self,
        url_template: str | None = None,
        tenors: Optional[Sequence[str]] = None,
        timeout_s: float = 30.0,
    ):
        self.url_template = url_template or self.DEFAULT_URL_TEMPLATE
        self.tenors = list(tenors) if tenors is not None else list(self._TENOR_TO_YEARS.keys())
        self.timeout_s = float(timeout_s)

    @property
    def name(self) -> str:
        return "treasury_par_curve"

    def fetch(self, as_of: Optional[date] = None) -> ParCurve:
        requests = require_requests()

        query_year = (as_of or date.today()).year
        url = self.url_template.format(year=query_year)
        resp = requests.get(url, timeout=self.timeout_s)
        resp.raise_for_status()

        reader = csv.DictReader(io.StringIO(resp.text))
        rows: List[Dict[str, str]] = [row for row in reader if row.get("Date")]
        if not rows:
            raise RuntimeError("Treasury CSV returned no rows.")

        if as_of is None:
            row = rows[-1]
        else:
            row = None
            target = as_of
            best_dt: Optional[date] = None
            for r in rows:
                dt = parse_date(r["Date"])
                if dt == target:
                    row = r
                    best_dt = dt
                    break
                if dt <= target and (best_dt is None or dt > best_dt):
                    row = r
                    best_dt = dt
            if row is None or best_dt is None:
                raise RuntimeError(f"No Treasury data found for {as_of.isoformat()} in {query_year}.")

        curve_date = parse_date(row["Date"])
        points: List[CurvePoint] = []
        for tenor in self.tenors:
            if tenor not in row:
                continue
            raw = (row[tenor] or "").strip()
            if raw in ("", "N/A"):
                continue
            y_pct = float(raw)
            points.append(CurvePoint(maturity_years=float(self._TENOR_TO_YEARS[tenor]), par_yield=y_pct / 100.0))

        if not points:
            raise RuntimeError(f"No curve points parsed for {curve_date.isoformat()}.")
        points.sort(key=lambda p: p.maturity_years)
        return ParCurve(as_of=curve_date, points=tuple(points))
