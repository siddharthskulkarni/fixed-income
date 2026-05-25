from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Literal, Tuple

ProductCode = Literal["SR1", "SR3"]


@dataclass(frozen=True)
class CurvePoint:
    maturity_years: float
    par_yield: float  # decimal, e.g. 0.045 for 4.5%


@dataclass(frozen=True)
class ParCurve:
    as_of: date
    points: Tuple[CurvePoint, ...]

    def as_dict(self) -> Dict[float, float]:
        return {p.maturity_years: p.par_yield for p in self.points}


@dataclass(frozen=True)
class RateObservation:
    date: date
    rate: float  # decimal, e.g. 0.0351 for 3.51%


@dataclass(frozen=True)
class RateSeries:
    series_id: str
    as_of: date
    observations: Tuple[RateObservation, ...]

    def as_of_value(self) -> float:
        if not self.observations:
            raise RuntimeError("RateSeries has no observations.")
        return self.observations[-1].rate

    def to_pandas(self):
        try:
            import pandas as pd
        except ImportError as e:  # pragma: no cover
            raise ImportError("pandas is required (install fixed-income[data]).") from e
        return pd.DataFrame(
            {"date": [o.date for o in self.observations], "rate": [o.rate for o in self.observations]}
        ).set_index("date")


@dataclass(frozen=True)
class FuturesSettle:
    product: ProductCode
    contract_month: str  # e.g. "MAY 26"
    settle: float
    symbol: str
    last: float | None = None
    volume: int | None = None


@dataclass(frozen=True)
class FuturesSettleCurve:
    as_of: date
    product: ProductCode
    settles: Tuple[FuturesSettle, ...]


@dataclass(frozen=True)
class SofrFuturesSettleBundle:
    as_of: date
    sr1: FuturesSettleCurve
    sr3: FuturesSettleCurve
