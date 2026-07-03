# Implementation Plan: Deploy

**Spec**: [spec.md](./spec.md)

## Summary

`src/server.py` — Flask factory with `/health` and protected `/run`. Root `app.py` — SnapDeploy entry. GHA workflow triggers daily run.

## Stack

- **HTTP**: Flask (minimal WSGI)
- **Port**: `PORT` env, default 8000
- **Auth**: `CRON_SECRET` from env

## Files

```text
app.py
src/server.py
.github/workflows/daily-alert.yml
tests/unit/test_server.py
```

## Constitution Check

✅ No secrets in code | ✅ Minimal diff | ✅ TDD
