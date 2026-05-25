from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Optional


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date format: {value!r}")


def require_requests():
    try:
        import requests  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("This feature requires `requests` (install `fixed-income[data]`).") from e
    return requests


def read_csv_dicts(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_csv_dicts_from_text(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


class DataSource(ABC):
    """
    Base class for data sources.

    Implementations should be deterministic for a given ``as_of`` and avoid returning
    partially-parsed/raw responses.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def fetch(self, as_of: Optional[date] = None) -> Any: ...
