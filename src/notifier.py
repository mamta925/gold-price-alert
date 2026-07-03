from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import AppConfig
from src.email_assets import GOLD_HEADER_CID, GOLD_HEADER_FILENAME, GOLD_HEADER_PATH
from src.templates import AlertMessage

logger = logging.getLogger(__name__)

EmailSendFn = Callable[[AppConfig, AlertMessage], bool]
WhatsAppSendFn = Callable[[AppConfig, AlertMessage], bool]


@dataclass(frozen=True)
class DispatchResult:
    email_sent: bool
    whatsapp_sent: bool


def build_email_message(config: AppConfig, message: AlertMessage) -> EmailMessage | MIMEMultipart:
    needs_inline_image = (
        message.body_html is not None
        and GOLD_HEADER_CID in message.body_html
        and GOLD_HEADER_PATH.is_file()
    )

    if message.body_html is None:
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = config.alert_email_from
        email["To"] = config.alert_email_to
        email.set_content(message.body)
        return email

    if not needs_inline_image:
        if GOLD_HEADER_CID in message.body_html and not GOLD_HEADER_PATH.is_file():
            logger.warning(
                "[4/5] Header image missing at %s — email will show broken image",
                GOLD_HEADER_PATH,
            )
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = config.alert_email_from
        email["To"] = config.alert_email_to
        email.set_content(message.body)
        email.add_alternative(message.body_html, subtype="html")
        return email

    root = MIMEMultipart("related")
    root["Subject"] = message.subject
    root["From"] = config.alert_email_from
    root["To"] = config.alert_email_to

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(message.body, "plain", "utf-8"))
    alternative.attach(MIMEText(message.body_html, "html", "utf-8"))
    root.attach(alternative)

    with GOLD_HEADER_PATH.open("rb") as img_file:
        image = MIMEImage(img_file.read(), _subtype="png")
    image.add_header("Content-ID", f"<{GOLD_HEADER_CID}>")
    image.add_header("Content-Disposition", "inline", filename=GOLD_HEADER_FILENAME)
    root.attach(image)
    return root


def _default_email_send(config: AppConfig, message: AlertMessage) -> bool:
    logger.info("[4/5] Sending email...")
    email = build_email_message(config, message)
    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as server:
        server.login(config.smtp_user, config.smtp_password)
        server.send_message(email)
    logger.info("[4/5] Email sent successfully")
    return True


def _default_whatsapp_send(config: AppConfig, message: AlertMessage) -> bool:
    from twilio.base.exceptions import TwilioRestException
    from twilio.rest import Client

    client = Client(config.twilio_account_sid, config.twilio_auth_token)
    body = f"{message.subject}\n\n{message.body}"
    logger.info("[5/5] Sending WhatsApp message...")
    try:
        result = client.messages.create(
            body=body,
            from_=config.twilio_whatsapp_from,
            to=config.twilio_whatsapp_to,
        )
    except TwilioRestException as exc:
        logger.error(
            "[5/5] WhatsApp error: twilio_code=%s status=%s msg=%s",
            exc.code,
            exc.status,
            exc.msg,
        )
        if exc.code == 63015:
            logger.error(
                "[5/5] Join Twilio WhatsApp sandbox: send join <code> to %s",
                config.twilio_whatsapp_from.removeprefix("whatsapp:"),
            )
        raise

    logger.info(
        "[5/5] WhatsApp sent successfully (sid=%s status=%s)",
        result.sid,
        result.status,
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
        except Exception as exc:
            logger.error("[4/5] Email error: %s", exc)
            return False

    def send_whatsapp(self, message: AlertMessage) -> bool:
        try:
            return self._whatsapp_send(self._config, message)
        except Exception as exc:
            logger.error("[5/5] WhatsApp error: %s", exc)
            return False

    def send_price_alert(self, message: AlertMessage) -> DispatchResult:
        logger.info("[4/5] Dispatching price alert (email + WhatsApp)...")
        result = DispatchResult(
            email_sent=self.send_email(message),
            whatsapp_sent=self.send_whatsapp(message),
        )
        if result.email_sent and result.whatsapp_sent:
            logger.info("[5/5] Price alert dispatched on both channels")
        elif result.email_sent:
            logger.warning("[5/5] Price alert partial: email ok, WhatsApp failed")
        elif result.whatsapp_sent:
            logger.warning("[5/5] Price alert partial: WhatsApp ok, email failed")
        else:
            logger.error("[5/5] Price alert failed on both channels")
        return result

    def send_system_alert(self, message: AlertMessage) -> DispatchResult:
        logger.info("[4/5] Dispatching system alert (email only)...")
        email_sent = self.send_email(message)
        if email_sent:
            logger.info("[4/5] System alert email sent")
        else:
            logger.error("[4/5] System alert email failed")
        return DispatchResult(
            email_sent=email_sent,
            whatsapp_sent=False,
        )
