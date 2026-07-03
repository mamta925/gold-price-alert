from unittest.mock import MagicMock

import pytest

from src.config import AppConfig
from src.email_assets import GOLD_HEADER_CID
from src.templates import AlertMessage
from src.notifier import DispatchResult, Notifier, build_email_message


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


def _message() -> AlertMessage:
    return AlertMessage(subject="Test subject", body="Test body")


class TestNotifier:
    def test_send_email_delegates_to_injected_fn(self) -> None:
        email_fn = MagicMock(return_value=True)
        notifier = Notifier(_config(), email_send_fn=email_fn)
        assert notifier.send_email(_message()) is True
        email_fn.assert_called_once()

    def test_send_whatsapp_delegates_to_injected_fn(self) -> None:
        whatsapp_fn = MagicMock(return_value=True)
        notifier = Notifier(_config(), whatsapp_send_fn=whatsapp_fn)
        assert notifier.send_whatsapp(_message()) is True
        whatsapp_fn.assert_called_once()

    def test_price_alert_sends_both_channels(self) -> None:
        email_fn = MagicMock(return_value=True)
        whatsapp_fn = MagicMock(return_value=True)
        notifier = Notifier(
            _config(),
            email_send_fn=email_fn,
            whatsapp_send_fn=whatsapp_fn,
        )
        result = notifier.send_price_alert(_message())
        assert result == DispatchResult(email_sent=True, whatsapp_sent=True)
        email_fn.assert_called_once()
        whatsapp_fn.assert_called_once()

    def test_system_alert_email_only(self) -> None:
        email_fn = MagicMock(return_value=True)
        whatsapp_fn = MagicMock(return_value=True)
        notifier = Notifier(
            _config(),
            email_send_fn=email_fn,
            whatsapp_send_fn=whatsapp_fn,
        )
        result = notifier.send_system_alert(_message())
        assert result == DispatchResult(email_sent=True, whatsapp_sent=False)
        email_fn.assert_called_once()
        whatsapp_fn.assert_not_called()

    def test_price_alert_propagates_partial_failure(self) -> None:
        notifier = Notifier(
            _config(),
            email_send_fn=lambda *_: True,
            whatsapp_send_fn=lambda *_: False,
        )
        result = notifier.send_price_alert(_message())
        assert result == DispatchResult(email_sent=True, whatsapp_sent=False)

    def test_build_email_message_attaches_inline_header_image(self) -> None:
        message = AlertMessage(
            subject="Gold Daily",
            body="plain text",
            body_html=f'<html><body><img src="cid:{GOLD_HEADER_CID}"></body></html>',
        )
        email = build_email_message(_config(), message)
        assert email.get_content_type() == "multipart/related"
        parts = list(email.walk())
        assert any(part.get_content_type() == "image/png" for part in parts)
        image_part = next(part for part in parts if part.get_content_type() == "image/png")
        assert image_part["Content-ID"] == f"<{GOLD_HEADER_CID}>"
