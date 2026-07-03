import pytest

from src.config import AppConfig, ConfigError, load_config


def _full_env(**overrides: str) -> dict[str, str]:
    base = {
        "SMTP_USER": "user@gmail.com",
        "SMTP_PASSWORD": "app-password",
        "ALERT_EMAIL_TO": "recipient@gmail.com",
        "TWILIO_ACCOUNT_SID": "ACtest",
        "TWILIO_AUTH_TOKEN": "token",
        "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
        "TWILIO_WHATSAPP_TO": "whatsapp:+919999999999",
    }
    base.update(overrides)
    return base


class TestLoadConfig:
    def test_loads_required_fields(self) -> None:
        config = load_config(_full_env())
        assert config.smtp_host == "smtp.gmail.com"
        assert config.smtp_port == 465
        assert config.smtp_user == "user@gmail.com"
        assert config.alert_email_from == "user@gmail.com"
        assert config.log_level == "INFO"

    def test_alert_email_from_override(self) -> None:
        config = load_config(_full_env(ALERT_EMAIL_FROM="alerts@gmail.com"))
        assert config.alert_email_from == "alerts@gmail.com"

    def test_missing_required_raises(self) -> None:
        env = _full_env()
        del env["SMTP_USER"]
        with pytest.raises(ConfigError, match="SMTP_USER"):
            load_config(env)

    def test_invalid_smtp_port_raises(self) -> None:
        with pytest.raises(ConfigError, match="SMTP_PORT"):
            load_config(_full_env(SMTP_PORT="not-a-number"))

    def test_loads_from_dotenv_file(self, tmp_path, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "\n".join(f"{key}={value}" for key, value in _full_env().items())
        )
        monkeypatch.chdir(tmp_path)
        for key in _full_env():
            monkeypatch.delenv(key, raising=False)
        config = load_config()
        assert config.smtp_user == "user@gmail.com"
