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


@dataclass(frozen=True)
class WindowBreach:
    window_key: str
    horizon_label: str
    n: int
    current: float
    previous_min: float


@dataclass(frozen=True)
class AnalysisResult:
    breach: WindowBreach | None


@dataclass(frozen=True)
class RunResult:
    fetch: FetchResult
    analysis: AnalysisResult
    inr_line: str | None = None

    @property
    def should_alert(self) -> bool:
        return (
            self.fetch.mode is not FetchMode.HARD_FAILURE
            and self.analysis.breach is not None
        )
