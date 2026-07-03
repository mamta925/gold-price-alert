from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.config import AppConfig
from src.main import run_daily_job
from src.models import FetchMode, FetchResult, TradingDayClose
from src.notifier import DispatchResult, Notifier
from src.templates import AlertMessage

IST = ZoneInfo("Asia/Kolkata")
FIXED_TS = datetime(2026, 7, 3, 8, 30, 15, tzinfo=IST)


def _config() -> AppConfig:
    return AppConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_user="from@gmail.com",
        smtp_password="secret",
        alert_email_to="to@gmail.com",
        alert_email_from="from@gmail.com",
        twilio_account_sid="ACtest",
        twilio_auth_token="token",
        twilio_whatsapp_from="whatsapp:+14155238886",
        twilio_whatsapp_to="whatsapp:+919999999999",
        log_level="INFO",
    )


def _fetch(mode: FetchMode, count: int) -> FetchResult:
    closes = [
        TradingDayClose(date=date(2024, 1, 1) + timedelta(days=i), close=2000.0 - i)
        for i in range(count)
    ]
    return FetchResult(mode=mode, trading_days=count, closes=closes)


def _notifier_recording() -> tuple[Notifier, list[AlertMessage], list[str]]:
    messages: list[AlertMessage] = []
    channels: list[str] = []

    def email_fn(_cfg: AppConfig, msg: AlertMessage) -> bool:
        messages.append(msg)
        channels.append("email")
        return True

    def whatsapp_fn(_cfg: AppConfig, msg: AlertMessage) -> bool:
        messages.append(msg)
        channels.append("whatsapp")
        return True

    notifier = Notifier(_config(), email_send_fn=email_fn, whatsapp_send_fn=whatsapp_fn)
    return notifier, messages, channels


class TestRunDailyJob:
    def test_hard_failure_sends_system_email_only(self) -> None:
        notifier, messages, channels = _notifier_recording()
        result = run_daily_job(
            config=_config(),
            fetch_fn=lambda: FetchResult(
                mode=FetchMode.HARD_FAILURE,
                trading_days=0,
                closes=[],
                error_code="CRITICAL_DATA_FETCH_ERROR",
            ),
            notifier=notifier,
            now_fn=lambda: FIXED_TS,
        )
        assert result.status == "hard_failure"
        assert len(result.notifications) == 1
        assert result.notifications[0] == DispatchResult(email_sent=True, whatsapp_sent=False)
        assert len(messages) == 1
        assert "CRITICAL_DATA_FETCH_ERROR" in messages[0].subject
        assert channels == ["email"]

    def test_fallback_no_breach_sends_degraded_email_and_daily_report(self) -> None:
        fetch = _fetch(FetchMode.FALLBACK, 180)
        fetch.closes[-1] = TradingDayClose(fetch.closes[-1].date, 5000.0)
        notifier, messages, channels = _notifier_recording()
        result = run_daily_job(
            config=_config(),
            fetch_fn=lambda: fetch,
            inr_fn=lambda: 83.0,
            notifier=notifier,
            now_fn=lambda: FIXED_TS,
        )
        assert result.status == "fallback_daily"
        assert len(messages) == 3
        assert "Fallback Data" in messages[0].subject
        assert "Gold Daily" in messages[1].subject
        assert channels == ["email", "email", "whatsapp"]

    def test_price_alert_sends_email_and_whatsapp(self) -> None:
        fetch = _fetch(FetchMode.FULL, 252)
        notifier, messages, channels = _notifier_recording()
        result = run_daily_job(
            config=_config(),
            fetch_fn=lambda: fetch,
            inr_fn=lambda: 83.0,
            notifier=notifier,
            now_fn=lambda: FIXED_TS,
        )
        assert result.status == "price_alert"
        assert result.run is not None
        assert result.run.should_alert is True
        assert len(result.notifications) == 1
        assert result.notifications[0].whatsapp_sent is True
        assert channels.count("email") == 1
        assert channels.count("whatsapp") == 1
        assert "GOLD ALERT" in messages[-1].subject

    def test_no_breach_sends_daily_report(self) -> None:
        fetch = _fetch(FetchMode.FULL, 252)
        fetch.closes[-1] = TradingDayClose(fetch.closes[-1].date, 5000.0)
        notifier, messages, channels = _notifier_recording()
        result = run_daily_job(
            config=_config(),
            fetch_fn=lambda: fetch,
            inr_fn=lambda: 83.0,
            notifier=notifier,
            now_fn=lambda: FIXED_TS,
        )
        assert result.status == "daily_report"
        assert len(result.notifications) == 1
        assert result.notifications[0].whatsapp_sent is True
        assert len(messages) == 2
        assert "Gold Daily" in messages[0].subject
        assert messages[0].body_html is not None
        assert channels == ["email", "whatsapp"]

    def test_fallback_price_alert_includes_addendum(self) -> None:
        fetch = _fetch(FetchMode.FALLBACK, 180)
        notifier, messages, channels = _notifier_recording()
        run_daily_job(
            config=_config(),
            fetch_fn=lambda: fetch,
            inr_fn=lambda: 83.0,
            notifier=notifier,
            now_fn=lambda: FIXED_TS,
        )
        assert channels == ["email", "email", "whatsapp"]
        price_body = messages[-1].body
        assert "fallback data (180 trading days" in price_body
        assert messages[-1].body_html is not None
