# Quality & Testing Guide: Notifier & Orchestration

**Feature**: `004-notifier-orchestration`  
**Last updated**: 2026-07-03 (rev 2)

## Commands

```bash
pytest tests/unit/test_config.py tests/unit/test_notifier.py tests/unit/test_main.py -v
pytest tests/unit/ -m "not integration"   # 82 passed
```

## Pipeline flow

```
fetch → hard failure? → system email (HTML) → exit
     → fallback? → degraded email (HTML)
     → analyze + INR → render_daily_alert() → email (HTML+text) + WhatsApp
```

## Notification routing

| Event | Email | WhatsApp |
|---|---|---|
| Daily gold report | ✅ HTML + plain | ✅ plain text |
| Fallback degraded notice | ✅ HTML + plain | ❌ |
| Hard failure | ✅ HTML + plain | ❌ |

## CID email check

Ensure `assets/gold-header.png` exists before deploy; notifier attaches inline when HTML references `cid:gold-header@gold-price-alert`.
