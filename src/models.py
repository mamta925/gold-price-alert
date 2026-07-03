from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pricing import IndiaGoldQuote

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

    def __repr__(self) -> str:
        return f"TradingDayClose({self.date}, {self.close:.2f})"


@dataclass(frozen=True)
class FetchResult:
    mode: FetchMode
    trading_days: int
    closes: list[TradingDayClose]
    error_code: str | None = None
    degraded_code: str | None = None
    expected_trading_days: int = EXPECTED_TRADING_DAYS

    def __repr__(self) -> str:
        latest = self.closes[-1] if self.closes else None
        latest_part = (
            f", latest={latest.close:.2f}@{latest.date}" if latest else ""
        )
        return (
            f"FetchResult(mode={self.mode.value!r}, trading_days={self.trading_days}"
            f"{latest_part})"
        )


@dataclass(frozen=True)
class WindowBreach:
    window_key: str
    horizon_label: str
    n: int
    current: float
    previous_min: float

    def __repr__(self) -> str:
        return (
            f"WindowBreach({self.window_key!r}, current={self.current:.2f}, "
            f"previous_min={self.previous_min:.2f})"
        )


@dataclass(frozen=True)
class AnalysisResult:
    breach: WindowBreach | None

    def __repr__(self) -> str:
        return f"AnalysisResult(breach={self.breach!r})"


@dataclass(frozen=True)
class RunResult:
    fetch: FetchResult
    analysis: AnalysisResult
    india_quote: IndiaGoldQuote | None = None

    @property
    def inr_line(self) -> str | None:
        if self.india_quote is None:
            return None
        from src.pricing import format_india_gold_summary

        return format_india_gold_summary(self.india_quote)

    @property
    def should_alert(self) -> bool:
        return (
            self.fetch.mode is not FetchMode.HARD_FAILURE
            and self.analysis.breach is not None
        )

    def __repr__(self) -> str:
        return (
            f"RunResult(should_alert={self.should_alert}, fetch={self.fetch!r}, "
            f"analysis={self.analysis!r})"
        )
