# Quality & Testing Guide: Deploy

**Feature**: `005-deploy` | **Last updated**: 2026-07-03

## Commands

```bash
pytest tests/unit/test_server.py -v
pytest tests/unit/ -m "not integration"   # 72 passed
python app.py                             # local server :5000
```

## Endpoints

| Endpoint | Auth |
|---|---|
| `GET /health` | None |
| `POST /run` | `X-Cron-Secret` or `?secret=` |

## GitHub Actions secrets

| Secret | Value |
|---|---|
| `SNAPDEPLOY_APP_URL` | SnapDeploy app base URL |
| `CRON_SECRET` | Same as SnapDeploy `CRON_SECRET` env |

Schedule: `0 3 * * *` UTC = **08:30 IST**
