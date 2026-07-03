# Contract: Config, Notifier, Main

## `src/config.py`

```python
class ConfigError(Exception): ...

@dataclass(frozen=True)
class AppConfig: ...

def load_config(environ: Mapping[str, str] | None = None) -> AppConfig: ...
```

## `src/notifier.py`

```python
@dataclass(frozen=True)
class DispatchResult:
    email_sent: bool
    whatsapp_sent: bool

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
    status: str  # hard_failure | fallback_silent | price_alert | silent
    run: RunResult | None
    notifications: list[DispatchResult]

def run_daily_job(...) -> JobResult: ...
```
