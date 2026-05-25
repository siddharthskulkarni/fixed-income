from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fixed_income.data.base import DataSource, read_csv_dicts
from fixed_income.data.types import (
    FuturesSettle,
    FuturesSettleCurve,
    ProductCode,
    SofrFuturesSettleBundle,
)

_CME_MONTH_CODE = {
    "JAN": "F",
    "FEB": "G",
    "MAR": "H",
    "APR": "J",
    "MAY": "K",
    "JUN": "M",
    "JUL": "N",
    "AUG": "Q",
    "SEP": "U",
    "OCT": "V",
    "NOV": "X",
    "DEC": "Z",
}


def _project_data_dir() -> Path:
    """``fixed-income/data`` directory (package parent / data)."""
    return Path(__file__).resolve().parents[2] / "data"


def default_cme_1m_path() -> Path:
    return _project_data_dir() / "raw" / "cme_1m_sofr_futures.csv"


def default_cme_3m_path() -> Path:
    return _project_data_dir() / "raw" / "cme_3m_sofr_futures.csv"


def parse_cme_price(raw: str) -> float | None:
    raw = (raw or "").strip()
    if raw in ("", "-"):
        return None
    while raw and raw[-1].isalpha():
        raw = raw[:-1]
    if not raw:
        return None
    return float(raw)


def month_label_to_symbol(product: ProductCode, month_label: str) -> str:
    """Map ``MAY 26`` + SR1/SR3 → ``SR1K6`` style CME Globex code."""
    parts = month_label.strip().upper().split()
    if len(parts) != 2:
        raise ValueError(f"Unrecognized contract month label: {month_label!r}")
    mon, yy = parts[0], parts[1]
    if mon not in _CME_MONTH_CODE:
        raise ValueError(f"Unrecognized month in label: {month_label!r}")
    if len(yy) != 2 or not yy.isdigit():
        raise ValueError(f"Unrecognized year in label: {month_label!r}")
    return f"{product}{_CME_MONTH_CODE[mon]}{yy[-1]}"


def parse_settle_csv(
    path: str | Path,
    product: ProductCode,
    trade_date: date,
) -> FuturesSettleCurve:
    rows = read_csv_dicts(str(path))
    settles: list[FuturesSettle] = []
    for row in rows:
        month = (row.get("Month") or "").strip()
        if not month:
            continue
        settle = parse_cme_price(row.get("Settle", ""))
        if settle is None:
            continue
        last = parse_cme_price(row.get("Last", ""))
        vol_raw = (row.get("Est. Volume") or row.get("Est Volume") or "").strip()
        volume = None
        if vol_raw and vol_raw != "-":
            try:
                volume = int(vol_raw.replace(",", ""))
            except ValueError:
                volume = None
        symbol = month_label_to_symbol(product, month)
        settles.append(
            FuturesSettle(
                product=product,
                contract_month=month,
                settle=settle,
                symbol=symbol,
                last=last,
                volume=volume,
            )
        )

    if not settles:
        raise RuntimeError(f"No settlement rows parsed from {path}.")

    return FuturesSettleCurve(as_of=trade_date, product=product, settles=tuple(settles))


class CmeSofrSettleCsvSource(DataSource):
    """
    CME SOFR futures settlement strip pasted from the quote board (CSV).

    The file does not include ``trade_date``; pass it at construction time.
    """

    def __init__(
        self,
        path: str | Path,
        product: ProductCode,
        trade_date: date,
    ):
        self.path = Path(path)
        self.product = product
        self.trade_date = trade_date

    @property
    def name(self) -> str:
        return f"cme:settle:{self.product.lower()}"

    def fetch(self, as_of: Optional[date] = None) -> FuturesSettleCurve:
        target = as_of or self.trade_date
        if target != self.trade_date:
            raise ValueError(
                f"{self.name} only has data for {self.trade_date.isoformat()}; "
                f"requested {target.isoformat()}."
            )
        if not self.path.is_file():
            raise FileNotFoundError(f"CME settle CSV not found: {self.path}")
        return parse_settle_csv(self.path, self.product, self.trade_date)


class CmeSofrSettleBundleSource(DataSource):
    """Load 1M (SR1) and 3M (SR3) settlement strips for a single trade date."""

    def __init__(
        self,
        trade_date: date,
        path_1m: str | Path | None = None,
        path_3m: str | Path | None = None,
    ):
        self.trade_date = trade_date
        self.path_1m = Path(path_1m) if path_1m is not None else default_cme_1m_path()
        self.path_3m = Path(path_3m) if path_3m is not None else default_cme_3m_path()

    @property
    def name(self) -> str:
        return "cme:settle:bundle"

    def fetch(self, as_of: Optional[date] = None) -> SofrFuturesSettleBundle:
        target = as_of or self.trade_date
        sr1 = CmeSofrSettleCsvSource(self.path_1m, "SR1", self.trade_date).fetch(as_of=target)
        sr3 = CmeSofrSettleCsvSource(self.path_3m, "SR3", self.trade_date).fetch(as_of=target)
        return SofrFuturesSettleBundle(as_of=target, sr1=sr1, sr3=sr3)
