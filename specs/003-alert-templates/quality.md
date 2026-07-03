# Quality & Testing Guide: Alert Templates

**Feature**: `003-alert-templates`  
**Module**: `src/templates.py`  
**Last updated**: 2026-07-03 (rev 2)

---

## Quick reference

| Command | What it does |
|---|---|
| `pytest tests/unit/test_templates.py -v` | Daily HTML + system template tests |
| `pytest tests/unit/ -v -m "not integration"` | Full unit suite (82 tests) |

---

## Example usage

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from src.analyzer import evaluate_windows
from src.models import TradingDayClose
from src.pricing import build_india_gold_quote
from src.templates import render_daily_alert

closes = [TradingDayClose(date=..., close=4191.50)]  # …252 rows
latest = closes[-1]
quote = build_india_gold_quote(latest.close, 86.5)

msg = render_daily_alert(
    latest=latest,
    breach=None,
    window_evaluations=evaluate_windows(closes),
    india_quote=quote,
    recent_closes=closes[-5:],
    timestamp=datetime.now(tz=ZoneInfo("Asia/Kolkata")),
)
print(msg.subject)      # 🪙 Gold Daily: $4,191.50, ~₹147,042.72
print(msg.body)         # plain text / WhatsApp
print(msg.body_html)    # HTML email
```

---

## PRD mapping

| Template | Function | PRD |
|---|---|---|
| Daily gold report | `render_daily_alert()` | §5.1 |
| Breach wrapper | `render_price_alert()` | §5.1 (delegates to daily) |
| Hard failure | `render_hard_failure_alert()` | §5.4 |
| Fallback degraded | `render_fallback_alert()` | §5.5 |
| Fallback addendum | `fallback_trading_days=` kwarg | §5.5 |

---

## Expected test count

```text
test_templates.py → all daily + system scenarios
Full unit suite   → 82 passed
```
