from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage

from src.config import AppConfig
from src.templates import AlertMessage

logger = logging.getLogger(__name__)

EmailSendFn = Callable[[AppConfig, AlertMessage], bool]
WhatsAppSendFn = Callable[[AppConfig, AlertMessage], bool]


@dataclass(frozen=True)
class DispatchResult:
    email_sent: bool
    whatsapp_sent: bool


def _default_email_send(config: AppConfig, message: AlertMessage) -> bool:
    email = EmailMessage()
    email["Subject"] = message.subject
    email["From"] = config.alert_email_from
    email["To"] = config.alert_email_to
    email.set_content(message.body)
    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as server:
        server.login(config.smtp_user, config.smtp_password)
        server.send_message(email)
    return True


def _default_whatsapp_send(config: AppConfig, message: AlertMessage) -> bool:
    from twilio.rest import Client

    client = Client(config.twilio_account_sid, config.twilio_auth_token)
    body = f"{message.subject}\n\n{message.body}"
    client.messages.create(
        body=body,
        from_=config.twilio_whatsapp_from,
        to=config.twilio_whatsapp_to,
    )
    return True


class Notifier:
    def __init__(
        self,
        config: AppConfig,
        *,
        email_send_fn: EmailSendFn = _default_email_send,
        whatsapp_send_fn: WhatsAppSendFn = _default_whatsapp_send,
    ) -> None:
        self._config = config
        self._email_send = email_send_fn
        self._whatsapp_send = whatsapp_send_fn

    def send_email(self, message: AlertMessage) -> bool:
        try:
            return self._email_send(self._config, message)
        except Exception:
            logger.exception("email dispatch failed")
            return False

    def send_whatsapp(self, message: AlertMessage) -> bool:
        try:
            return self._whatsapp_send(self._config, message)
        except Exception:
            logger.exception("whatsapp dispatch failed")
            return False

    def send_price_alert(self, message: AlertMessage) -> DispatchResult:
        return DispatchResult(
            email_sent=self.send_email(message),
            whatsapp_sent=self.send_whatsapp(message),
        )

    def send_system_alert(self, message: AlertMessage) -> DispatchResult:
        return DispatchResult(
            email_sent=self.send_email(message),
            whatsapp_sent=False,
        )
