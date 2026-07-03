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
    → POST https://goldpricealert.containers.snapdeploy.dev/run
       Header: X-Cron-Secret: <CRON_SECRET>
    → SnapDeploy wakes container (~1 min cold start)
    → App runs once: fetch → analyze → email + WhatsApp
    → Container sleeps again
```

**Live app URL:** `https://goldpricealert.containers.snapdeploy.dev`

SnapDeploy has **no built-in cron**. GitHub Actions is the scheduler; SnapDeploy is the runtime.

### Who receives alerts

Configured via SnapDeploy environment variables:

| Variable | Purpose |
|---|---|
| `ALERT_EMAIL_TO` | Email recipient(s) — comma-separated for multiple |
| `TWILIO_WHATSAPP_TO` | WhatsApp recipient (Twilio sandbox or production number) |

Every successful run sends a **daily gold report** (email + WhatsApp). If gold is at a trailing historical low, the same report highlights the breach. Hard fetch failures send **email only**.

---

## Adding / changing recipients

Recipients are controlled by **SnapDeploy environment variables** — no code change needed. After editing, **redeploy/restart** the container so the new values load.

### Add an email recipient

1. SnapDeploy → container → **Environment variables** → edit **`ALERT_EMAIL_TO`**
2. Add addresses **comma-separated, no spaces**:
   ```
   ALERT_EMAIL_TO=mamtarajput925@gmail.com,ptiwari248@gmail.com,newperson@gmail.com
   ```
3. Save and redeploy. All listed addresses receive every alert.

### Add a WhatsApp recipient

WhatsApp uses the **Twilio sandbox**, so a new number needs **two steps**:

1. **Join the sandbox from the new phone.** On that phone's WhatsApp, send `join <your-sandbox-code>` to **+1 415 523 8886**. Get the code from Twilio Console → **Messaging → Try it out → Send a WhatsApp message**. Wait for "✅ You are all set!"
2. SnapDeploy → **Environment variables** → set **`TWILIO_WHATSAPP_TO`** with the `whatsapp:` prefix:
   ```
   TWILIO_WHATSAPP_TO=whatsapp:+919672338162
   ```
3. Save and redeploy.

**Note:** the sandbox delivers to **one** `TWILIO_WHATSAPP_TO` number, and each recipient must join the sandbox first. Sandbox joins expire after **72 hours** of inactivity — resend `join <code>` if messages stop. To send to multiple numbers or skip the join step, upgrade to a Twilio **paid WhatsApp sender** (out of scope for the free sandbox).

---

## Setup checklist

1. Push code to GitHub.
2. [SnapDeploy](https://snapdeploy.dev) → **New Container** → connect this repo (entry: `app.py`).
3. Set env vars in SnapDeploy dashboard — see `.env.example` and `prd.md` Section 8.
4. Add GitHub repository secrets (Settings → Secrets and variables → Actions → **Repository secrets**):
   - `SNAPDEPLOY_APP_URL` — `https://goldpricealert.containers.snapdeploy.dev` (no trailing slash)
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

Optional: `SMTP_HOST`, `SMTP_PORT`, `ALERT_EMAIL_FROM`, `LOG_LEVEL`, `PORT` (default 5000).

**Build note:** the `Dockerfile` installs the runtime deps **directly** (not via `requirements.txt`), because SnapDeploy's build scanner otherwise injects stdlib `zoneinfo` and dev-only `pytest`, which break `pip`. Never add `zoneinfo`, `hmac`, or `pytest` as pip packages.

Generate a strong `CRON_SECRET`:

```bash
openssl rand -hex 32
```

Set the **same** value in SnapDeploy env vars and GitHub repository secret `CRON_SECRET`.

---

## Manual trigger

**GitHub Actions:** Actions → **Daily Gold Alert** → **Run workflow**

**curl** (replace secret):

```bash
curl -sf -X POST \
  -H "X-Cron-Secret: YOUR_SECRET" \
  https://goldpricealert.containers.snapdeploy.dev/run
```

**Health check** (no auth):

```bash
curl https://goldpricealert.containers.snapdeploy.dev/health
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
curl http://localhost:5000/health
curl -X POST -H "X-Cron-Secret: YOUR_SECRET" http://localhost:5000/run
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

### Deployment stuck on “Wait for Service Stable” / “WAIT_FOR_HEALTHY”

First deploy can take **5–10 minutes**. If it stays stuck longer:

1. Open SnapDeploy → **Logs** for this container. Look for `ModuleNotFoundError: gunicorn`, crash loops, or port errors.
2. Ensure the `Dockerfile` installs **`gunicorn`** and runs it (SnapDeploy runs Gunicorn, not Flask’s dev server).
3. Confirm **`GET /health`** returns 200 once the URL is live:
   ```bash
   curl https://goldpricealert.containers.snapdeploy.dev/health
   ```
4. In SnapDeploy container settings, set **`PORT=5000`** if auto-detection picked the wrong port.

After fixing, push to GitHub and **redeploy** (or cancel the stuck deploy and start a new one).

### Build failed: `No matching distribution found for zoneinfo`

SnapDeploy **Smart Build** injects stdlib modules (`zoneinfo`, `hmac`) or `pytest` into the requirements it installs. Do **not** use Smart Build auto-fix. The `Dockerfile` avoids this by installing runtime deps directly instead of from `requirements.txt` — keep it that way.

### Deploy blocked demanding a PostgreSQL add-on

SnapDeploy's keyword scanner flags any occurrence of a database name in the repo. This app uses **no database** — do not create PostgreSQL. Ensure no file contains database keywords like "PostgreSQL" (a Spec Kit template example previously triggered this).

### Port mismatch / `EXPOSE` warning

Keep everything on **5000**: `Dockerfile` `EXPOSE 5000`, gunicorn bind `5000`, and Container Port `5000` in the dashboard.

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
