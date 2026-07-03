# Quality & Testing Guide: Notifier & Orchestration

**Feature**: `004-notifier-orchestration`  
**Last updated**: 2026-07-03

## Commands

```bash
pytest tests/unit/test_config.py tests/unit/test_notifier.py tests/unit/test_main.py -v
pytest tests/unit/ -m "not integration"   # 65 passed
```

## Pipeline flow

```
fetch → hard failure? → system email → exit
     → fallback? → degraded email
     → analyze → breach? → price email + WhatsApp
              → no breach → silent
```

## Notification routing

| Event | Email | WhatsApp |
|---|---|---|
| Price alert | ✅ | ✅ |
| Fallback degraded | ✅ | ❌ |
| Hard failure | ✅ | ❌ |
| No breach | ❌ | ❌ |
