# Deployment — SnapDeploy + GitHub Actions

Production hosting for the Gold Price Alert app. For local development, see [README.md](README.md).

---

## Architecture

| Component | Role |
|---|---|
| **SnapDeploy** | Hosts the Python container (free tier: 512 MB, auto-sleep/wake, GitHub deploy) |
| **GitHub Actions** | Fires daily at **08:30 IST** → `POST` to SnapDeploy `/run` (wakes container) |
| **This repo** | Source code; connect to SnapDeploy via GitHub integration |

### Daily flow

```
GitHub Actions (08:30 IST daily)
    → POST https://your-app.snapdeploy.dev/run
       Header: X-Cron-Secret: <CRON_SECRET>
    → SnapDeploy wakes container (~1 min cold start)
    → App runs once: fetch → analyze → email + WhatsApp
    → Container sleeps again
```

SnapDeploy has **no built-in cron**. GitHub Actions is the scheduler; SnapDeploy is the runtime.

### Who receives alerts

Configured via SnapDeploy environment variables:

| Variable | Purpose |
|---|---|
| `ALERT_EMAIL_TO` | Email recipient(s) — comma-separated for multiple |
| `TWILIO_WHATSAPP_TO` | WhatsApp recipient (Twilio sandbox or production number) |

Every successful run sends a **daily gold report** (email + WhatsApp). If gold is at a trailing historical low, the same report highlights the breach. Hard fetch failures send **email only**.

---

## Setup checklist

1. Push code to GitHub.
2. [SnapDeploy](https://snapdeploy.dev) → **New Container** → connect this repo (entry: `app.py`).
3. Set env vars in SnapDeploy dashboard — see `.env.example` and `prd.md` Section 8.
4. Add GitHub repository secrets (Settings → Secrets and variables → Actions → **Repository secrets**):
   - `SNAPDEPLOY_APP_URL` — e.g. `https://your-app.snapdeploy.dev` (no trailing slash)
   - `CRON_SECRET` — **same value** as SnapDeploy `CRON_SECRET`
5. Enable workflow: `.github/workflows/daily-alert.yml` (runs daily **08:30 IST**).

---

## Environment variables

Copy `.env.example` for the full list. Required on SnapDeploy:

| Variable | Required | Notes |
|---|---|---|
| `SMTP_USER`, `SMTP_PASSWORD` | Yes | Gmail app password (no spaces) |
| `ALERT_EMAIL_TO` | Yes | Recipient email(s) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Yes | Twilio Console |
| `TWILIO_WHATSAPP_FROM`, `TWILIO_WHATSAPP_TO` | Yes | Sandbox: recipient must `join <code>` first |
| `CRON_SECRET` | Yes | You create this — not issued by SnapDeploy |

Optional: `SMTP_HOST`, `SMTP_PORT`, `ALERT_EMAIL_FROM`, `LOG_LEVEL`, `PORT`.

**Do not** add `zoneinfo`, `hmac`, or `pytest` to `requirements.txt` — they are stdlib or dev-only. Production deps are only the 5 lines in `requirements.txt`.

Generate a strong `CRON_SECRET`:

```bash
openssl rand -hex 32
```

Set the **same** value in SnapDeploy env vars and GitHub repository secret `CRON_SECRET`.

---

## Manual trigger

**GitHub Actions:** Actions → **Daily Gold Alert** → **Run workflow**

**curl** (replace URL and secret):

```bash
curl -sf -X POST \
  -H "X-Cron-Secret: YOUR_SECRET" \
  https://your-app.snapdeploy.dev/run
```

**Health check** (no auth):

```bash
curl https://your-app.snapdeploy.dev/health
```

---

## Local HTTP smoke test (before deploy)

```bash
cp .env.example .env   # fill in SMTP, Twilio, CRON_SECRET
pip install -r requirements.txt
python app.py
```

In another terminal:

```bash
curl http://localhost:8000/health
curl -X POST -H "X-Cron-Secret: YOUR_SECRET" http://localhost:8000/run
```

---

## Schedule

| When | What |
|---|---|
| **08:30 IST** every day | GitHub Actions cron (`0 3 * * *` UTC) |
| Manual | GitHub **Run workflow** or `curl POST /run` |

First scheduled run happens at the next **08:30 IST** after secrets and deploy are green. GitHub cron can be a few minutes late.

---

## Troubleshooting

### Build failed: `No matching distribution found for zoneinfo`

SnapDeploy **Smart Build** may inject stdlib modules (`zoneinfo`, `hmac`) or `pytest` into requirements. Do **not** use Smart Build auto-fix. Redeploy from the repo’s 5-line `requirements.txt` on `master`.

### Workflow fails: `Missing SNAPDEPLOY_APP_URL or CRON_SECRET`

Add both as **Repository secrets** under GitHub Settings → Secrets and variables → Actions.

### `POST /run` returns 401

`CRON_SECRET` on SnapDeploy does not match the header value (or GitHub secret).

### `POST /run` returns 503

`CRON_SECRET` is not set on SnapDeploy.

### WhatsApp not delivered

Recipient must join the Twilio sandbox: send `join <your-code>` to `+1 415 523 8886` on WhatsApp. Code is in Twilio Console → Messaging → Try it out.

### Deploy quota

Free tier: 5 deploys per 12 hours. One daily wake uses 1 run/day — well within limits. Uncheck auto-deploy on every push if you hit the limit during development.

---

## Free tier usage

1 wake/run per day ≪ SnapDeploy’s daily limit. No credit card required for the free tier.
