from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.models import (
    CRITICAL_DATA_FETCH_ERROR,
    EXPECTED_TRADING_DAYS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    WindowBreach,
)
from src.templates import (
    format_timestamp_ist,
    render_fallback_alert,
    render_hard_failure_alert,
    render_price_alert,
    skipped_window_labels,
)

IST = ZoneInfo("Asia/Kolkata")
FIXED_TS = datetime(2026, 7, 3, 8, 30, 15, tzinfo=IST)


def _breach(window_key: str, horizon: str, n: int) -> WindowBreach:
    return WindowBreach(
        window_key=window_key,
        horizon_label=horizon,
        n=n,
        current=1945.20,
        previous_min=1952.00,
    )


@pytest.mark.parametrize(
    ("window_key", "horizon", "n", "subject_phrase"),
    [
        ("1y", "1 year", 252, "1 year"),
        ("6m", "6 months", 126, "6 months"),
        ("3m", "3 months", 63, "3 months"),
        ("1m", "1 month", 21, "1 month"),
        ("15d", "15 days", 15, "15 days"),
        ("10d", "10 days", 10, "10 days"),
    ],
)
class TestWindowSpecificSubjects:
    def test_subject_contains_horizon_and_price(
        self,
        window_key: str,
        horizon: str,
        n: int,
        subject_phrase: str,
    ) -> None:
        msg = render_price_alert(
            _breach(window_key, horizon, n),
            inr_line=None,
            timestamp=FIXED_TS,
        )
        assert msg.subject == (
            f"🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last {subject_phrase}"
        )


class TestPriceAlertBody:
    def test_body_includes_usd_values_and_timestamp(self) -> None:
        msg = render_price_alert(
            _breach("1y", "1 year", 252),
            inr_line=None,
            timestamp=FIXED_TS,
        )
        assert "Gold trailing-low alert (GC=F)" in msg.body
        assert "📉 Today is the lowest Gold close (GC=F) in the last **1 year**." in msg.body
        assert "Previous low: $1,952.00 → Today: $1,945.20" in msg.body
        assert "Timestamp: 2026-07-03 08:30:15 IST" in msg.body
        assert "Action: Evaluate current entry positions." in msg.body

    def test_body_includes_inr_line_when_provided(self) -> None:
        inr_line = (
            "India parity: ₹1,11,450.00 / 10g "
            "(24K international parity per 10g (excl. import duty, GST, local premium))"
        )
        msg = render_price_alert(
            _breach("1y", "1 year", 252),
            inr_line=inr_line,
            timestamp=FIXED_TS,
        )
        assert inr_line in msg.body

    def test_body_omits_inr_when_none(self) -> None:
        msg = render_price_alert(
            _breach("1y", "1 year", 252),
            inr_line=None,
            timestamp=FIXED_TS,
        )
        assert "India parity:" not in msg.body

    def test_body_appends_fallback_addendum(self) -> None:
        msg = render_price_alert(
            _breach("6m", "6 months", 126),
            inr_line=None,
            timestamp=FIXED_TS,
            fallback_trading_days=180,
        )
        assert (
            "⚠️ Note: This alert used fallback data "
            "(180 trading days available, not full 252-day / 1-year history)."
        ) in msg.body

    def test_body_omits_fallback_addendum_in_full_mode(self) -> None:
        msg = render_price_alert(
            _breach("1y", "1 year", 252),
            inr_line=None,
            timestamp=FIXED_TS,
            fallback_trading_days=None,
        )
        assert "fallback data" not in msg.body


class TestHardFailureTemplate:
    def test_subject_and_body(self) -> None:
        msg = render_hard_failure_alert(trading_days=0, timestamp=FIXED_TS)
        assert msg.subject == f"⛔ GOLD ALERT ENGINE: {CRITICAL_DATA_FETCH_ERROR}"
        assert CRITICAL_DATA_FETCH_ERROR in msg.body
        assert "Trading days received: 0" in msg.body
        assert f"Retries exhausted: {MAX_RETRIES} attempts with {RETRY_DELAY_SECONDS}s delay" in msg.body
        assert "Timestamp: 2026-07-03 08:30:15 IST" in msg.body
        assert "No low-detection was performed." in msg.body


class TestFallbackTemplate:
    def test_lists_skipped_windows(self) -> None:
        msg = render_fallback_alert(trading_days=180, timestamp=FIXED_TS)
        assert msg.subject == "⚠️ GOLD ALERT ENGINE: Running on Fallback Data (180 days)"
        assert f"Expected: {EXPECTED_TRADING_DAYS} trading days" in msg.body
        assert "Received: 180 trading days" in msg.body
        assert "Mode: FALLBACK" in msg.body
        assert "Skipped windows: 1-Year" in msg.body
        assert "6-Month" not in msg.body.split("Skipped windows:")[1].split("\n")[0]


class TestHelpers:
    def test_format_timestamp_ist_from_utc(self) -> None:
        utc = datetime(2026, 7, 3, 3, 0, 15, tzinfo=ZoneInfo("UTC"))
        assert format_timestamp_ist(utc) == "2026-07-03 08:30:15 IST"

    def test_skipped_window_labels(self) -> None:
        assert skipped_window_labels(180) == ["1-Year"]
        assert skipped_window_labels(252) == []
