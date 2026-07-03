from __future__ import annotations

from dataclasses import dataclass

from src.models import TradingDayClose, WindowBreach


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


def analyze_lows(closes: list[TradingDayClose]) -> WindowBreach | None:
    if len(closes) < 10:
        return None

    current = closes[-1].close

    for window in WINDOWS_TOP_DOWN:
        if window.n > len(closes):
            continue

        window_closes = closes[-window.n :]
        window_min = min(day.close for day in window_closes)
        if current <= window_min:
            prior = window_closes[:-1]
            previous_min = min(day.close for day in prior) if prior else current
            return WindowBreach(
                window_key=window.key,
                horizon_label=window.horizon_label,
                n=window.n,
                current=current,
                previous_min=previous_min,
            )

    return None
