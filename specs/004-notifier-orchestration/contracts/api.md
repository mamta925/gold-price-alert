# Contract: Config, Notifier, Main

## `src/config.py`

```python
class ConfigError(Exception): ...

@dataclass(frozen=True)
class AppConfig: ...

def load_config(environ: Mapping[str, str] | None = None) -> AppConfig: ...
```

## `src/email_assets.py`

```python
GOLD_HEADER_CID = "gold-header@gold-price-alert"
GOLD_HEADER_PATH: Path  # repo/assets/gold-header.png
GOLD_HEADER_IMAGE_SRC = f"cid:{GOLD_HEADER_CID}"
```

## `src/notifier.py`

```python
@dataclass(frozen=True)
class DispatchResult:
    email_sent: bool
    whatsapp_sent: bool

def build_email_message(config: AppConfig, message: AlertMessage) -> EmailMessage | MIMEMultipart:
    """Plain EmailMessage or multipart/related with CID PNG when body_html references header."""

class Notifier:
    def send_email(self, message: AlertMessage) -> bool: ...
    def send_whatsapp(self, message: AlertMessage) -> bool: ...
    def send_price_alert(self, message: AlertMessage) -> DispatchResult: ...
    def send_system_alert(self, message: AlertMessage) -> DispatchResult: ...
```

## `src/main.py`

```python
@dataclass(frozen=True)
class JobResult:
    status: str  # hard_failure | daily_report | fallback_daily | price_alert | fallback_price_alert
    run: RunResult | None
    notifications: tuple[DispatchResult, ...]

def run_daily_job(...) -> JobResult: ...
```

### Pipeline postconditions

| Fetch mode | System email | Daily report (Email + WhatsApp) |
|---|---|---|
| `HARD_FAILURE` | Hard failure Email | No |
| `FALLBACK` | Degraded Email, then daily report | Yes |
| `FULL` | No | Yes |

Daily report always uses `render_daily_alert()` with `evaluate_windows()` and last 5 closes.
