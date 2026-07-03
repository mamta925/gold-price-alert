from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.analyzer import evaluate_windows
from src.models import (
    CRITICAL_DATA_FETCH_ERROR,
    EXPECTED_TRADING_DAYS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    TradingDayClose,
    WindowBreach,
)
from src.email_assets import GOLD_HEADER_CID, GOLD_HEADER_IMAGE_SRC
from src.pricing import build_india_gold_quote
from src.templates import (
    format_timestamp_ist,
    render_daily_alert,
    render_fallback_alert,
    render_hard_failure_alert,
    render_price_alert,
    skipped_window_labels,
)

IST = ZoneInfo("Asia/Kolkata")
FIXED_TS = datetime(2026, 7, 3, 8, 30, 15, tzinfo=IST)
LATEST = TradingDayClose(date=date(2026, 7, 2), close=1945.20)


def _breach(window_key: str, horizon: str, n: int) -> WindowBreach:
    return WindowBreach(
        window_key=window_key,
        horizon_label=horizon,
        n=n,
        current=1945.20,
        previous_min=1952.00,
    )


def _evaluations_for_breach(breach: WindowBreach) -> list:
    closes = [
        TradingDayClose(date=date(2026, 6, 24), close=3990.30),
        TradingDayClose(date=date(2026, 6, 26), close=4078.70),
        TradingDayClose(date=date(2026, 6, 29), close=4022.30),
        TradingDayClose(date=date(2026, 6, 30), close=4022.90),
        TradingDayClose(date=date(2026, 7, 1), close=4068.30),
        TradingDayClose(date=date(2026, 7, 2), close=1945.20),
    ]
    return evaluate_windows(closes)


def _recent_closes() -> list[TradingDayClose]:
    return [
        TradingDayClose(date=date(2026, 6, 26), close=4078.70),
        TradingDayClose(date=date(2026, 6, 29), close=4022.30),
        TradingDayClose(date=date(2026, 6, 30), close=4022.90),
        TradingDayClose(date=date(2026, 7, 1), close=4068.30),
        TradingDayClose(date=date(2026, 7, 2), close=4195.80),
    ]


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
        breach = _breach(window_key, horizon, n)
        msg = render_daily_alert(
            latest=LATEST,
            breach=breach,
            window_evaluations=_evaluations_for_breach(breach),
            india_quote=None,
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
        )
        assert msg.subject == (
            f"🚨 GOLD ALERT: $1,945.20 — Lowest in the last {subject_phrase}"
        )


class TestDailyAlertBody:
    def test_body_includes_usd_values_and_timestamp(self) -> None:
        breach = _breach("1y", "1 year", 252)
        msg = render_daily_alert(
            latest=LATEST,
            breach=breach,
            window_evaluations=_evaluations_for_breach(breach),
            india_quote=None,
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
        )
        assert "Gold Daily Report (GC=F)" in msg.body
        assert "Today's close: $1,945.20" in msg.body
        assert "Today is the lowest close in the last 1 year" in msg.body
        assert "Previous low: $1,952.00 → Today: $1,945.20" in msg.body
        assert "Timestamp: 2026-07-03 08:30:15 IST" in msg.body
        assert "Action: Evaluate current entry positions." in msg.body

    def test_no_breach_body_states_not_at_low(self) -> None:
        msg = render_daily_alert(
            latest=TradingDayClose(date=date(2026, 7, 2), close=4195.80),
            breach=None,
            window_evaluations=_evaluations_for_breach(_breach("10d", "10 days", 10)),
            india_quote=None,
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
        )
        assert msg.subject == "🪙 Gold Daily: $4,195.80 — Not at trailing low"
        assert "Today is not at a trailing low" in msg.body
        assert "Action:" not in msg.body

    def test_body_includes_india_quote_when_provided(self) -> None:
        quote = build_india_gold_quote(1945.20, 83.0)
        msg = render_daily_alert(
            latest=LATEST,
            breach=_breach("1y", "1 year", 252),
            window_evaluations=_evaluations_for_breach(_breach("1y", "1 year", 252)),
            india_quote=quote,
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
        )
        assert "International parity:" in msg.body
        assert "India retail estimate:" in msg.body
        assert "/ 10g" in msg.body
        assert "/ g" in msg.body
        assert quote.retail_per_10g > quote.parity_per_10g

    def test_body_omits_india_quote_when_none(self) -> None:
        msg = render_daily_alert(
            latest=LATEST,
            breach=_breach("1y", "1 year", 252),
            window_evaluations=_evaluations_for_breach(_breach("1y", "1 year", 252)),
            india_quote=None,
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
        )
        assert "International parity:" not in msg.body
        assert "India retail estimate:" not in msg.body

    def test_body_appends_fallback_addendum(self) -> None:
        msg = render_daily_alert(
            latest=LATEST,
            breach=_breach("6m", "6 months", 126),
            window_evaluations=_evaluations_for_breach(_breach("6m", "6 months", 126)),
            india_quote=None,
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
            fallback_trading_days=180,
        )
        assert (
            "⚠️ Note: This report used fallback data "
            "(180 trading days available, not full 252-day / 1-year history)."
        ) in msg.body

    def test_window_scan_includes_last_five_days_column(self) -> None:
        recent = _recent_closes()
        closes = [
            TradingDayClose(date=date(2024, 1, 1) + timedelta(days=i), close=5000.0 - i)
            for i in range(252)
        ]
        closes[-5:] = recent
        latest = closes[-1]
        msg = render_daily_alert(
            latest=latest,
            breach=None,
            window_evaluations=evaluate_windows(closes),
            india_quote=None,
            recent_closes=recent,
            timestamp=FIXED_TS,
        )
        assert msg.body_html is not None
        assert "Last 5 days" in msg.body_html
        assert ">Last 5 Days<" not in msg.body_html
        assert "Last 5 days: Low $4,022.30 on 2026-06-29 — above low" in msg.body
        assert "2026-06-26: $4,078.70" not in msg.body

    def test_html_includes_gold_coin_and_india_pricing(self) -> None:
        msg = render_daily_alert(
            latest=LATEST,
            breach=None,
            window_evaluations=_evaluations_for_breach(_breach("10d", "10 days", 10)),
            india_quote=build_india_gold_quote(1945.20, 83.0),
            recent_closes=_recent_closes(),
            timestamp=FIXED_TS,
        )
        assert msg.body_html is not None
        assert GOLD_HEADER_IMAGE_SRC in msg.body_html
        assert "India retail estimate" in msg.body_html
        assert "~ ₹" in msg.body_html
        assert "font-size:46px" in msg.body_html

    def test_render_price_alert_wrapper_still_works(self) -> None:
        closes = [
            TradingDayClose(date=date(2026, 6, 24), close=3990.30),
            TradingDayClose(date=date(2026, 7, 2), close=1945.20),
        ]
        msg = render_price_alert(
            _breach("10d", "10 days", 10),
            india_quote=None,
            timestamp=FIXED_TS,
            window_closes=closes,
        )
        assert msg.body_html is not None
        assert "TRAILING LOW" in msg.body_html


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
