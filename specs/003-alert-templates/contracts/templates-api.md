# Contract: Templates Module API

**Feature**: `003-alert-templates` | **Module**: `src/templates.py`

## Public Types

```python
@dataclass(frozen=True)
class AlertMessage:
    subject: str
    body: str
    body_html: str | None = None
```

## Public Constants

```python
RECENT_TRADING_DAYS = 5  # Last-N summary row in window scan
```

## Public Functions

### `render_daily_alert`

```python
def render_daily_alert(
    *,
    latest: TradingDayClose,
    breach: WindowBreach | None,
    window_evaluations: list[WindowEvaluation],
    india_quote: IndiaGoldQuote | None,
    recent_closes: list[TradingDayClose],
    timestamp: datetime,
    fallback_trading_days: int | None = None,
) -> AlertMessage:
    """Render unified daily gold report (HTML + plain text) per prd.md §5.1."""
```

### `render_price_alert`

```python
def render_price_alert(
    breach: WindowBreach,
    *,
    india_quote: IndiaGoldQuote | None,
    timestamp: datetime,
    fallback_trading_days: int | None = None,
    window_closes: list[TradingDayClose] | None = None,
) -> AlertMessage:
    """Legacy wrapper — delegates to render_daily_alert() with breach set."""
```

### `render_hard_failure_alert`

```python
def render_hard_failure_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    """Render CRITICAL_DATA_FETCH_ERROR email (HTML + plain) per prd.md §5.4."""
```

### `render_fallback_alert`

```python
def render_fallback_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    """Render degraded-data email (HTML + plain) per prd.md §5.5."""
```

### `format_timestamp_ist`

```python
def format_timestamp_ist(dt: datetime) -> str:
    """Format as YYYY-MM-DD HH:MM:SS IST (Asia/Kolkata)."""
```

### `skipped_window_labels`

```python
def skipped_window_labels(trading_days: int) -> list[str]:
    """PRD skip labels for windows where N > trading_days."""
```

## HTML Email Contract

- Daily and system alerts set `body_html` with shared dark/gold shell (`_wrap_email_document`).
- Daily HTML header image src: `cid:gold-header@gold-price-alert` (see `src/email_assets.py`).
- Notifier MUST attach `assets/gold-header.png` as `MIMEImage` with matching Content-ID when CID present.

**Side effects**: None (pure functions)
