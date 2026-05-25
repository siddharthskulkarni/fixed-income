from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

import numpy as np

from fixed_income.data.types import RateSeries


@dataclass(frozen=True)
class DiscountCurve:
    """OIS-style discount factors P(0, T) anchored at ``as_of`` (P=1 at t=0)."""

    as_of: date
    pillars: tuple[float, ...]
    discount_factors: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.pillars) != len(self.discount_factors):
            raise ValueError("pillars and discount_factors must have the same length")
        if len(self.pillars) == 0:
            raise ValueError("DiscountCurve requires at least one pillar")

    def discount(self, t: float) -> float:
        """Interpolate P(0, t) in log-space for year fraction ``t``."""
        t = float(t)
        if t <= 0:
            return 1.0
        pillars = np.asarray(self.pillars, dtype=float)
        dfs = np.asarray(self.discount_factors, dtype=float)
        if t <= pillars[0]:
            return float(dfs[0]) if t == pillars[0] else float(dfs[0] ** (t / pillars[0]))
        if t >= pillars[-1]:
            return float(dfs[-1] ** (t / pillars[-1]))
        log_dfs = np.log(np.clip(dfs, 1e-12, None))
        log_p = np.interp(t, pillars, log_dfs)
        return float(np.exp(log_p))


def _act360_fraction(d0: date, d1: date) -> float:
    return (d1 - d0).days / 360.0


def _pillar_to_date(as_of: date, pillar_years: float) -> date:
    return as_of + timedelta(days=int(round(float(pillar_years) * 365.25)))


def bootstrap_ois_from_sofr(
    rate_series: RateSeries,
    pillars: Sequence[float],
    *,
    day_count: str = "ACT/360",
) -> DiscountCurve:
    """
    Bootstrap OIS discount factors by compounding overnight SOFR fixings.

    Notes:
    - Normalizes P(as_of) = 1.
    - Uses published fixings on/ before ``rate_series.as_of``; flat-forwards
      with the last SOFR rate for dates after the last fixing up to each pillar.
    - Simplified single-curve model (not full OIS swap mechanics).
    """
    if day_count != "ACT/360":
        raise ValueError("Only ACT/360 day_count is supported")

    as_of = rate_series.as_of
    obs = sorted(
        [o for o in rate_series.observations if o.date <= as_of],
        key=lambda o: o.date,
    )
    if not obs:
        raise ValueError("RateSeries has no observations on or before as_of")

    rate_by_date = {o.date: o.rate for o in obs}
    last_rate = obs[-1].rate

    def compound_to(target: date) -> float:
        if target < as_of:
            raise ValueError("pillar date must be on or after as_of for forward bootstrap")
        schedule = sorted({as_of, target, *rate_by_date.keys()})
        schedule = [d for d in schedule if as_of <= d <= target]
        if schedule[0] != as_of:
            schedule = [as_of] + schedule
        if schedule[-1] != target:
            schedule = schedule + [target]

        growth = 1.0
        for i in range(1, len(schedule)):
            d0, d1 = schedule[i - 1], schedule[i]
            dt = _act360_fraction(d0, d1)
            if dt <= 0:
                continue
            r = rate_by_date.get(d0, last_rate)
            growth *= 1.0 + r * dt
        return 1.0 / growth

    pillar_list = tuple(float(p) for p in pillars)
    dfs: list[float] = []
    for pillar in pillar_list:
        end = _pillar_to_date(as_of, pillar)
        dfs.append(compound_to(end))

    return DiscountCurve(as_of=as_of, pillars=pillar_list, discount_factors=tuple(dfs))


def forward_rate_from_discount(curve: DiscountCurve, t1: float, t2: float) -> float:
    """
    Simple forward rate between year fractions ``t1`` and ``t2`` (t2 > t1).

    Returns continuously compounded style rate from discount ratio.
    """
    t1, t2 = float(t1), float(t2)
    if t2 <= t1:
        raise ValueError("t2 must be greater than t1")
    p1 = curve.discount(t1)
    p2 = curve.discount(t2)
    dt = t2 - t1
    return (p1 / p2 - 1.0) / dt
