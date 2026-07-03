from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

CRITICAL_DATA_FETCH_ERROR = "CRITICAL_DATA_FETCH_ERROR"
DATA_FETCH_DEGRADED = "DATA_FETCH_DEGRADED"
EXPECTED_TRADING_DAYS = 252
FALLBACK_MIN_DAYS = 10
TICKER_DEFAULT = "GC=F"
HISTORY_PERIOD = "1y"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60


class FetchMode(str, Enum):
    FULL = "full"
    FALLBACK = "fallback"
    HARD_FAILURE = "hard_failure"


@dataclass(frozen=True)
class TradingDayClose:
    date: date
    close: float


@dataclass(frozen=True)
class FetchResult:
    mode: FetchMode
    trading_days: int
    closes: list[TradingDayClose]
    error_code: str | None = None
    degraded_code: str | None = None
    expected_trading_days: int = EXPECTED_TRADING_DAYS
