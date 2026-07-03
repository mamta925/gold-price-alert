from datetime import date, timedelta

import pytest

from src.models import (
    AnalysisResult,
    FetchMode,
    FetchResult,
    TradingDayClose,
    WindowBreach,
)
from src.service import GoldAlertService


def _fetch_result(mode: FetchMode, count: int, *, end: float = 2000.0) -> FetchResult:
    closes = [
        TradingDayClose(date=date(2024, 1, 1) + timedelta(days=i), close=end - i)
        for i in range(count)
    ]
    return FetchResult(mode=mode, trading_days=count, closes=closes)


class TestGoldAlertService:
    def test_hard_failure_skips_analysis(self) -> None:
        service = GoldAlertService(
            fetch_fn=lambda: FetchResult(
                mode=FetchMode.HARD_FAILURE,
                trading_days=0,
                closes=[],
                error_code="CRITICAL_DATA_FETCH_ERROR",
            )
        )
        result = service.run()
        assert result.fetch.mode is FetchMode.HARD_FAILURE
        assert result.analysis.breach is None
        assert result.should_alert is False

    def test_no_breach_returns_without_inr(self) -> None:
        fetch = _fetch_result(FetchMode.FULL, 252, end=3000.0)
        fetch.closes[-1] = TradingDayClose(fetch.closes[-1].date, 4000.0)
        service = GoldAlertService(fetch_fn=lambda: fetch)
        result = service.run()
        assert result.should_alert is False
        assert result.inr_line is None

    def test_breach_includes_inr_line_when_rate_available(self) -> None:
        fetch = _fetch_result(FetchMode.FULL, 252)
        service = GoldAlertService(
            fetch_fn=lambda: fetch,
            inr_fn=lambda: 83.0,
        )
        result = service.run()
        assert result.should_alert is True
        assert result.analysis.breach is not None
        assert result.analysis.breach.window_key == "1y"
        assert result.inr_line is not None
        assert "India parity:" in result.inr_line

    def test_breach_without_inr_still_alerts(self) -> None:
        fetch = _fetch_result(FetchMode.FULL, 252)
        service = GoldAlertService(fetch_fn=lambda: fetch, inr_fn=lambda: None)
        result = service.run()
        assert result.should_alert is True
        assert result.inr_line is None

    def test_fallback_mode_still_computes(self) -> None:
        fetch = _fetch_result(FetchMode.FALLBACK, 180)
        service = GoldAlertService(fetch_fn=lambda: fetch, inr_fn=lambda: 83.0)
        result = service.run()
        assert result.fetch.mode is FetchMode.FALLBACK
        assert result.should_alert is True
        assert result.analysis.breach is not None
        assert result.analysis.breach.window_key == "6m"
