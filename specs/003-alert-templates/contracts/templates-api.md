# Contract: Templates Module API

**Feature**: `003-alert-templates` | **Module**: `src/templates.py`

## Public Types

```python
@dataclass(frozen=True)
class AlertMessage:
    subject: str
    body: str
```

## Public Functions

### `render_price_alert`

```python
def render_price_alert(
    breach: WindowBreach,
    *,
    inr_line: str | None,
    timestamp: datetime,
    fallback_trading_days: int | None = None,
) -> AlertMessage:
    """Render window-specific price alert per prd.md §5.1."""
```

### `render_hard_failure_alert`

```python
def render_hard_failure_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    """Render CRITICAL_DATA_FETCH_ERROR email per prd.md §5.3."""
```

### `render_fallback_alert`

```python
def render_fallback_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    """Render degraded-data email per prd.md §5.4."""
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

**Side effects**: None (pure functions)
