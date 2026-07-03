from datetime import date, timedelta

import pandas as pd
import pytest

from src.fetcher import (
    classify_mode,
    fetch_gold_closes,
    normalize_closes,
)
from src.models import (
    CRITICAL_DATA_FETCH_ERROR,
    DATA_FETCH_DEGRADED,
    EXPECTED_TRADING_DAYS,
    FetchMode,
)


def _make_closes_df(n: int, start: date | None = None) -> pd.DataFrame:
    start = start or date(2025, 1, 1)
    index = pd.to_datetime([start + timedelta(days=i) for i in range(n)])
    return pd.DataFrame({"Close": [1900.0 + i for i in range(n)]}, index=index)


class TestClassifyMode:
    def test_full_at_252(self) -> None:
        mode, error, degraded = classify_mode(252)
        assert mode is FetchMode.FULL
        assert error is None
        assert degraded is None

    def test_full_above_252(self) -> None:
        mode, _, _ = classify_mode(300)
        assert mode is FetchMode.FULL

    def test_fallback_at_251(self) -> None:
        mode, error, degraded = classify_mode(251)
        assert mode is FetchMode.FALLBACK
        assert error is None
        assert degraded == DATA_FETCH_DEGRADED

    def test_fallback_at_10(self) -> None:
        mode, _, degraded = classify_mode(10)
        assert mode is FetchMode.FALLBACK
        assert degraded == DATA_FETCH_DEGRADED

    def test_hard_failure_at_9(self) -> None:
        mode, error, degraded = classify_mode(9)
        assert mode is FetchMode.HARD_FAILURE
        assert error == CRITICAL_DATA_FETCH_ERROR
        assert degraded is None

    def test_hard_failure_at_zero(self) -> None:
        mode, error, _ = classify_mode(0)
        assert mode is FetchMode.HARD_FAILURE
        assert error == CRITICAL_DATA_FETCH_ERROR


class TestNormalizeCloses:
    def test_valid_dataframe(self) -> None:
        df = _make_closes_df(3)
        closes = normalize_closes(df)
        assert len(closes) == 3
        assert closes[0].date < closes[-1].date
        assert all(c.close > 0 for c in closes)

    def test_drops_nan_and_invalid(self) -> None:
        df = pd.DataFrame(
            {"Close": [1900.0, float("nan"), 0.0, -1.0, 1905.0]},
            index=pd.to_datetime(
                ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
            ),
        )
        closes = normalize_closes(df)
        assert len(closes) == 2
        assert closes[0].close == 1900.0
        assert closes[1].close == 1905.0

    def test_dedupes_dates_keeps_last(self) -> None:
        df = pd.DataFrame(
            {"Close": [1900.0, 1999.0]},
            index=pd.to_datetime(["2025-01-01", "2025-01-01"]),
        )
        closes = normalize_closes(df)
        assert len(closes) == 1
        assert closes[0].close == 1999.0

    def test_empty_dataframe(self) -> None:
        assert normalize_closes(pd.DataFrame()) == []


class TestFetchGoldCloses:
    def test_full_mode_with_mocked_yfinance(self, mocker) -> None:
        mocker.patch(
            "src.fetcher._fetch_history",
            return_value=_make_closes_df(252),
        )
        result = fetch_gold_closes(sleep_fn=lambda _: None)
        assert result.mode is FetchMode.FULL
        assert result.trading_days == 252
        assert len(result.closes) == 252
        assert result.error_code is None

    def test_latest_close_is_last_row(self, mocker) -> None:
        mocker.patch(
            "src.fetcher._fetch_history",
            return_value=_make_closes_df(252, start=date(2024, 6, 1)),
        )
        result = fetch_gold_closes(sleep_fn=lambda _: None)
        assert result.closes[-1].date == date(2024, 6, 1) + timedelta(days=251)
        assert result.closes[-1].close == 1900.0 + 251

    def test_retry_succeeds_on_second_attempt(self, mocker) -> None:
        fetch = mocker.patch("src.fetcher._fetch_history")
        fetch.side_effect = [pd.DataFrame(), _make_closes_df(252)]
        sleep = mocker.Mock()
        result = fetch_gold_closes(sleep_fn=sleep)
        assert result.mode is FetchMode.FULL
        assert fetch.call_count == 2
        sleep.assert_called_once_with(60)

    def test_hard_failure_after_three_failures(self, mocker) -> None:
        mocker.patch(
            "src.fetcher._fetch_history",
            side_effect=RuntimeError("network"),
        )
        sleep = mocker.Mock()
        result = fetch_gold_closes(sleep_fn=sleep)
        assert result.mode is FetchMode.HARD_FAILURE
        assert result.error_code == CRITICAL_DATA_FETCH_ERROR
        assert result.closes == []
        assert sleep.call_count == 2

    def test_empty_dataframe_triggers_retry(self, mocker) -> None:
        fetch = mocker.patch("src.fetcher._fetch_history")
        fetch.side_effect = [pd.DataFrame(), pd.DataFrame(), _make_closes_df(252)]
        sleep = mocker.Mock()
        result = fetch_gold_closes(sleep_fn=sleep)
        assert result.mode is FetchMode.FULL
        assert fetch.call_count == 3
        assert sleep.call_count == 2

    def test_fallback_mode_180_days(self, mocker) -> None:
        mocker.patch(
            "src.fetcher._fetch_history",
            return_value=_make_closes_df(180),
        )
        result = fetch_gold_closes(sleep_fn=lambda _: None)
        assert result.mode is FetchMode.FALLBACK
        assert result.degraded_code == DATA_FETCH_DEGRADED
        assert result.trading_days == 180
        assert result.expected_trading_days == EXPECTED_TRADING_DAYS

    def test_hard_failure_below_10_days(self, mocker) -> None:
        mocker.patch(
            "src.fetcher._fetch_history",
            return_value=_make_closes_df(5),
        )
        result = fetch_gold_closes(sleep_fn=lambda _: None)
        assert result.mode is FetchMode.HARD_FAILURE
        assert result.error_code == CRITICAL_DATA_FETCH_ERROR
        assert result.closes == []
        assert result.trading_days == 0

    def test_fallback_preserves_all_valid_closes(self, mocker) -> None:
        df = _make_closes_df(180)
        mocker.patch("src.fetcher._fetch_history", return_value=df)
        result = fetch_gold_closes(sleep_fn=lambda _: None)
        assert len(result.closes) == 180
        assert result.closes[0].close == 1900.0
        assert result.closes[-1].close == 1900.0 + 179


@pytest.mark.integration
def test_live_fetch_gc_f() -> None:
    result = fetch_gold_closes()
    assert result.mode in (FetchMode.FULL, FetchMode.FALLBACK)
    assert result.trading_days >= 10
    assert result.closes[-1].close > 0
