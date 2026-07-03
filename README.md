# Gold Price Alert

Automated **daily gold report** for Gold Futures (`GC=F`) with **trailing historical low** detection. Sends HTML email and WhatsApp each morning with USD close, India pricing estimate, and a multi-horizon window scan.

**Production deploy:** [deployment.md](deployment.md) (SnapDeploy + GitHub Actions at 08:30 IST).

---

## What it does

Each run:

1. **Fetches** ~1 year of daily closes from Yahoo Finance (`GC=F`)
2. **Analyzes** trailing windows (1 year → 6 months → 3 months → 1 month → 15 days → 10 days) top-down — first matching low wins
3. **Builds** a daily report with India 24K reference pricing (`GC=F` + `INR=X`)
4. **Sends** email (HTML) + WhatsApp (plain text) to configured recipients

| Outcome | Notification |
|---|---|
| Normal day (not at a trailing low) | Daily report — “not at low” |
| Today is lowest in a window (e.g. 1 year) | Daily report — breach highlighted |
| Partial data (10–251 days) | Degraded-data email + daily report |
| Hard fetch failure | Critical email only |

No database, no web UI — one headless job per trigger.

---

## How it runs in production

```
08:30 IST daily
    GitHub Actions  ──POST /run + CRON_SECRET──►  SnapDeploy (wakes app)
                                                         │
                                                         ▼
                                              fetch → analyze → notify
                                                         │
                                                         ▼
                                              Email + WhatsApp to you
```

- **Scheduler:** GitHub Actions (`.github/workflows/daily-alert.yml`)
- **Runtime:** SnapDeploy container (`app.py` → Flask `/health` + `/run`)
- **Secrets:** SnapDeploy env vars + matching GitHub repository secrets

Full setup: **[deployment.md](deployment.md)**

---

## Run locally

### Prerequisites

- Python 3.11+
- SMTP (Gmail app password) and Twilio WhatsApp credentials for live notifications

### Setup

```bash
git clone https://github.com/mamta925/gold-price-alert.git
cd gold-price-alert
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env        # fill in values — never commit .env
```

### Tests

```bash
pytest tests/unit/ -v -m "not integration"
```

Live Yahoo fetch (optional, needs network):

```bash
pytest tests/unit/ -v -m integration
```

### Start the HTTP server

```bash
python app.py
```

Default port **8000**. Endpoints:

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | No | Liveness check |
| `POST` | `/run` | `X-Cron-Secret` header or `?secret=` | Run the alert pipeline once |

Smoke test:

```bash
curl http://localhost:8000/health
curl -X POST -H "X-Cron-Secret: YOUR_SECRET" http://localhost:8000/run
```

(`YOUR_SECRET` must match `CRON_SECRET` in `.env`.)

### Run the pipeline without HTTP

```bash
python -c "from src.main import run_daily_job; print(run_daily_job())"
```

Requires full `.env` (SMTP + Twilio) to send notifications.

---

## Project layout

```
gold-price-alert/
├── app.py                 # Flask entry (SnapDeploy)
├── src/
│   ├── fetcher.py         # Yahoo Finance GC=F
│   ├── analyzer.py        # Trailing-low detection
│   ├── service.py         # Orchestration
│   ├── templates.py       # Email/WhatsApp content
│   ├── notifier.py        # SMTP + Twilio
│   ├── main.py            # Daily job pipeline
│   └── server.py          # /health, /run
├── tests/unit/
├── .github/workflows/     # Daily 08:30 IST trigger
├── deployment.md          # SnapDeploy + GitHub Actions guide
├── prd.md                 # Full requirements
└── specs/                 # Feature specs (Spec Kit)
```

---

## Spec-Driven Development (Spec Kit)

This project uses [GitHub Spec Kit](https://github.com/github/spec-kit) with Cursor Agent.

```
1. /speckit-constitution   → .specify/memory/constitution.md
2. /speckit-specify        → specs/NNN-feature/spec.md
3. /speckit-plan           → plan.md, data-model.md, contracts/
4. /speckit-tasks          → tasks.md
5. /speckit-implement      → TDD implementation
```

Approve `spec.md`, `plan.md`, and `tasks.md` before `/speckit-implement`. Requirements source of truth: **`prd.md`**.

---

## Secrets

Copy `.env.example` → `.env` for local use. Production secrets go in **SnapDeploy** env vars and **GitHub Actions** repository secrets — never in git. See [deployment.md](deployment.md).
