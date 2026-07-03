from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 465
DEFAULT_LOG_LEVEL = "INFO"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class AppConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    alert_email_to: str
    alert_email_from: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    twilio_whatsapp_to: str
    log_level: str


def _require(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value


def load_config(environ: Mapping[str, str] | None = None) -> AppConfig:
    if environ is None:
        from dotenv import load_dotenv

        env_path = Path(".env")
        if env_path.is_file():
            load_dotenv(env_path)
    env = dict(os.environ if environ is None else environ)

    smtp_user = _require(env, "SMTP_USER")
    smtp_password = _require(env, "SMTP_PASSWORD")
    alert_email_to = _require(env, "ALERT_EMAIL_TO")
    twilio_account_sid = _require(env, "TWILIO_ACCOUNT_SID")
    twilio_auth_token = _require(env, "TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from = _require(env, "TWILIO_WHATSAPP_FROM")
    twilio_whatsapp_to = _require(env, "TWILIO_WHATSAPP_TO")

    smtp_host = env.get("SMTP_HOST", DEFAULT_SMTP_HOST).strip() or DEFAULT_SMTP_HOST
    log_level = env.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip() or DEFAULT_LOG_LEVEL
    alert_email_from = env.get("ALERT_EMAIL_FROM", "").strip() or smtp_user

    port_raw = env.get("SMTP_PORT", str(DEFAULT_SMTP_PORT)).strip()
    try:
        smtp_port = int(port_raw)
    except ValueError as exc:
        raise ConfigError(f"Invalid SMTP_PORT: {port_raw}") from exc

    return AppConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        alert_email_to=alert_email_to,
        alert_email_from=alert_email_from,
        twilio_account_sid=twilio_account_sid,
        twilio_auth_token=twilio_auth_token,
        twilio_whatsapp_from=twilio_whatsapp_from,
        twilio_whatsapp_to=twilio_whatsapp_to,
        log_level=log_level,
    )
