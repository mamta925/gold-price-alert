# Implementation Plan: Notifier & Orchestration

**Branch**: `004-notifier-orchestration` | **Spec**: [spec.md](./spec.md)

## Summary

`config.py` loads env; `notifier.py` sends Email/WhatsApp with DI; `main.py` wires fetch → system emails → `GoldAlertService` → price alert templates → notifier.

## Files

```text
src/config.py
src/notifier.py
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
| Email+WhatsApp price only | ✅ |
| Minimal diff | ✅ |
