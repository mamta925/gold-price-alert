from datetime import date, timedelta

import pytest

from src.analyzer import WINDOWS_TOP_DOWN, analyze_lows
from src.models import FetchMode, FetchResult, TradingDayClose


def _closes(n: int, *, end: float = 2000.0, step: float = 1.0) -> list[TradingDayClose]:
    start = date(2024, 1, 1)
    return [
        TradingDayClose(date=start + timedelta(days=i), close=end - (i * step))
        for i in range(n)
    ]


class TestAnalyzeLows:
    def test_new_low_triggers_longest_window_first(self) -> None:
        closes = _closes(252, end=2000.0, step=0.5)
        breach = analyze_lows(closes)
        assert breach is not None
        assert breach.window_key == "1y"
        assert breach.n == 252

    def test_short_circuit_does_not_return_shorter_window(self) -> None:
        closes = _closes(252, end=2000.0, step=0.5)
        breach = analyze_lows(closes)
        assert breach is not None
        assert breach.window_key != "10d"

    def test_no_breach_when_today_not_lowest(self) -> None:
        closes = _closes(252, end=2000.0, step=0.5)
        closes[-1] = TradingDayClose(closes[-1].date, 2100.0)
        assert analyze_lows(closes) is None

    def test_skips_ineligible_long_windows_in_fallback(self) -> None:
        closes = _closes(180, end=2000.0, step=0.5)
        breach = analyze_lows(closes)
        assert breach is not None
        assert breach.window_key == "6m"
        assert breach.n == 126

    def test_tie_at_window_low_triggers(self) -> None:
        closes = _closes(10, end=100.0, step=0.0)
        breach = analyze_lows(closes)
        assert breach is not None
        assert breach.current == 100.0

    def test_previous_min_excludes_today(self) -> None:
        closes = _closes(10, end=100.0, step=1.0)
        closes[-1] = TradingDayClose(closes[-1].date, 90.0)
        breach = analyze_lows(closes)
        assert breach is not None
        assert breach.current == 90.0
        assert breach.previous_min == 92.0

    def test_insufficient_data_returns_none(self) -> None:
        assert analyze_lows(_closes(9)) is None

    def test_windows_ordered_top_down(self) -> None:
        assert [w.n for w in WINDOWS_TOP_DOWN] == [252, 126, 63, 21, 15, 10]
