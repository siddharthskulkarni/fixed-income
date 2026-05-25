from __future__ import annotations

import json
import os
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fixed_income.data.base import DataSource
from fixed_income.data.types import (
    CurvePoint,
    FuturesSettle,
    FuturesSettleCurve,
    ParCurve,
    RateObservation,
    RateSeries,
    SofrFuturesSettleBundle,
)

_REGISTRY = {
    "CurvePoint": CurvePoint,
    "ParCurve": ParCurve,
    "RateObservation": RateObservation,
    "RateSeries": RateSeries,
    "FuturesSettle": FuturesSettle,
    "FuturesSettleCurve": FuturesSettleCurve,
    "SofrFuturesSettleBundle": SofrFuturesSettleBundle,
}


def _default_cache_dir() -> Path:
    raw = os.getenv("FIXED_INCOME_DATA_DIR")
    if raw:
        return Path(raw)
    return Path.home() / ".cache" / "fixed-income"


def _encode(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return {"__type__": "date", "value": obj.isoformat()}
    if is_dataclass(obj) and not isinstance(obj, type):
        return {
            "__type__": type(obj).__name__,
            "fields": {f.name: _encode(getattr(obj, f.name)) for f in fields(obj)},
        }
    if isinstance(obj, tuple):
        return {"__type__": "tuple", "items": [_encode(x) for x in obj]}
    if isinstance(obj, dict):
        return {str(k): _encode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_encode(x) for x in obj]
    return obj


def _decode(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_decode(x) for x in obj]
    if isinstance(obj, dict):
        if "__type__" in obj:
            kind = obj["__type__"]
            if kind == "date":
                return date.fromisoformat(obj["value"])
            if kind == "tuple":
                return tuple(_decode(x) for x in obj["items"])
            cls = _REGISTRY.get(kind)
            if cls is None:
                raise ValueError(f"Unknown cached type: {kind!r}")
            return cls(**{k: _decode(v) for k, v in obj["fields"].items()})
        return {k: _decode(v) for k, v in obj.items()}
    return obj


class CachedDataSource(DataSource):
    """Wrap a ``DataSource`` with JSON disk cache."""

    def __init__(
        self,
        source: DataSource,
        cache_dir: str | Path | None = None,
        max_age_hours: float = 24.0,
    ):
        self.source = source
        self.cache_dir = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
        self.max_age = timedelta(hours=float(max_age_hours))

    @property
    def name(self) -> str:
        return f"cached:{self.source.name}"

    def _cache_path(self, as_of: Optional[date]) -> Path:
        key = as_of.isoformat() if as_of is not None else "latest"
        safe = self.source.name.replace(":", "_")
        return self.cache_dir / safe / f"{key}.json"

    def fetch(self, as_of: Optional[date] = None) -> Any:
        path = self._cache_path(as_of)
        if path.is_file():
            age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
            if age <= self.max_age:
                return _decode(json.loads(path.read_text(encoding="utf-8")))

        result = self.source.fetch(as_of=as_of)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_encode(result), indent=2), encoding="utf-8")
        return result
