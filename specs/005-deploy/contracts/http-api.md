# Contract: HTTP Server

**Module**: `src/server.py` | **Entry**: `app.py`

## Endpoints

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | None | `200 {"status":"ok"}` |
| POST | `/run` | `X-Cron-Secret` or `?secret=` | `200` job JSON or `401`/`503` |

## Auth

Compare provided secret to `CRON_SECRET` env var (constant-time compare).

## JSON response (`POST /run`)

```json
{
  "status": "price_alert",
  "fetch_mode": "full",
  "trading_days": 252,
  "should_alert": true,
  "window_key": "1y",
  "notifications": [{"email_sent": true, "whatsapp_sent": true}]
}
```

## Factory

```python
def create_app(
    run_job_fn=run_daily_job,
    cron_secret_fn: Callable[[], str | None] | None = None,
) -> Flask: ...
```
