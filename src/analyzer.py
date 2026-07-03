"""Trailing-low analyzer — top-down window evaluation.

Evaluation rules:
- **No** on a window → try the next shorter window
- **Yes** on a window → return breach and stop
- **No on all** eligible windows → return None (silent exit)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.models import TradingDayClose, WindowBreach

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WindowDefinition:
    key: str
    horizon_label: str
    n: int


WINDOWS_TOP_DOWN: tuple[WindowDefinition, ...] = (
    WindowDefinition("1y", "1 year", 252),
    WindowDefinition("6m", "6 months", 126),
    WindowDefinition("3m", "3 months", 63),
    WindowDefinition("1m", "1 month", 21),
    WindowDefinition("15d", "15 days", 15),
    WindowDefinition("10d", "10 days", 10),
)

def min_close_day(closes: list[TradingDayClose]) -> TradingDayClose:
    return min(closes, key=lambda day: day.close)


def _min_close_day(closes: list[TradingDayClose]) -> TradingDayClose:
    return min_close_day(closes)


def _log_window_result(
    window: WindowDefinition,
    *,
    current: float,
    window_closes: list[TradingDayClose],
    triggered: bool,
) -> None:
    min_day = _min_close_day(window_closes)
    outcome = "TRIGGER (stop)" if triggered else "no (continue)"
    logger.info(
        "[3/5] Window %s (N=%s): current=%.2f window_min=%.2f @%s → %s",
        window.key,
        window.n,
        current,
        min_day.close,
        min_day.date,
        outcome,
    )


def analyze_lows(closes: list[TradingDayClose]) -> WindowBreach | None:
    if len(closes) < 10:
        return None

    current = closes[-1].close

    for window in WINDOWS_TOP_DOWN:
        if window.n > len(closes):
            logger.info(
                "[3/5] Window %s (N=%s trading days): skipped — only %s days available",
                window.key,
                window.n,
                len(closes),
            )
            continue

        window_closes = closes[-window.n :]
        window_min = min(day.close for day in window_closes)
        if current <= window_min:
            _log_window_result(
                window, current=current, window_closes=window_closes, triggered=True
            )
            prior = window_closes[:-1]
            previous_min = min(day.close for day in prior) if prior else current
            return WindowBreach(
                window_key=window.key,
                horizon_label=window.horizon_label,
                n=window.n,
                current=current,
                previous_min=previous_min,
            )

        _log_window_result(
            window, current=current, window_closes=window_closes, triggered=False
        )

    return None
