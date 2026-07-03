# Quality & Testing Guide: Alert Templates

**Feature**: `003-alert-templates`  
**Module**: `src/templates.py`  
**Last updated**: 2026-07-03

---

## Quick reference

| Command | What it does |
|---|---|
| `pytest tests/unit/test_templates.py -v` | 15 template tests |
| `pytest tests/unit/ -v -m "not integration"` | Full suite (51 tests) |

---

## Example usage

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from src.models import WindowBreach
from src.templates import render_price_alert

breach = WindowBreach(
    window_key="1y",
    horizon_label="1 year",
    n=252,
    current=1945.20,
    previous_min=1952.00,
)
msg = render_price_alert(
    breach,
    inr_line="India parity: ₹1,11,450.00 / 10g (...)",
    timestamp=datetime.now(tz=ZoneInfo("Asia/Kolkata")),
)
print(msg.subject)
print(msg.body)
```

---

## PRD mapping

| Template | Function | PRD |
|---|---|---|
| Price alert (6 windows) | `render_price_alert()` | §5.1 |
| Hard failure | `render_hard_failure_alert()` | §5.3 |
| Fallback degraded | `render_fallback_alert()` | §5.4 |
| Fallback addendum | `fallback_trading_days=` kwarg | §5.4 |

---

## Expected test count

```text
test_templates.py → 15 passed
Full unit suite   → 51 passed, 1 deselected
```
