# Implementation Plan: Notifier & Orchestration

**Branch**: `004-notifier-orchestration` | **Spec**: [spec.md](./spec.md) (rev 2)

## Summary

`config.py` loads env; `notifier.py` sends multipart HTML Email (CID header) + WhatsApp plain text; `main.py` wires fetch → system emails → `GoldAlertService` → `render_daily_alert()` → notifier on **every successful run**.

## Files

```text
src/config.py
src/notifier.py
src/email_assets.py
assets/gold-header.png
src/main.py
.env.example
tests/unit/test_config.py
tests/unit/test_notifier.py
tests/unit/test_main.py
```

## Dependencies

Add `twilio` to `requirements.txt` (pinned).

## Constitution Check

| Gate | Status |
|---|---|
| TDD | ✅ |
| No secrets in code | ✅ |
| Email+WhatsApp daily report | ✅ |
| Minimal diff | ✅ |
