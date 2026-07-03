# Gold Price Alert

Automated **trailing historical low** alerts for Gold Futures (`GC=F`) — headless Python job on **[SnapDeploy](https://snapdeploy.dev)** with Email + WhatsApp notifications.

## Deployment (SnapDeploy + GitHub Actions)

| Component | Role |
|---|---|
| **SnapDeploy** | Hosts the Python container (free tier: 512 MB, auto-sleep/wake, GitHub deploy) |
| **GitHub Actions** | Fires daily at **08:30 IST** → `POST` to SnapDeploy `/run` (wakes container) |
| **This repo** | Source code; connect to SnapDeploy via GitHub integration |

### Setup checklist

1. Push code to GitHub.
2. [SnapDeploy](https://snapdeploy.dev) → **New Container** → connect this repo (entry: `app.py`).
3. Set env vars in SnapDeploy dashboard — see `.env.example` and `prd.md` Section 8.
4. Add GitHub repository secrets: `SNAPDEPLOY_APP_URL` (e.g. `https://your-app.snapdeploy.dev`), `CRON_SECRET` (same value as SnapDeploy).
5. Enable workflow: `.github/workflows/daily-alert.yml` (runs daily **08:30 IST**).

### Local HTTP smoke test

```bash
export CRON_SECRET=local-dev-secret
# plus SMTP/Twilio vars from .env.example
python app.py
curl http://localhost:8000/health
curl -X POST -H "X-Cron-Secret: local-dev-secret" http://localhost:8000/run
```

**Free tier usage:** 1 wake/run per day ≪ 10 daily limit. No credit card required.

## Spec-Driven Development (Spec Kit — minimal)

This project uses [GitHub Spec Kit](https://github.com/github/spec-kit) with **Cursor Agent** (lean setup — core workflow only).

### Repo layout

```
gold-price-alert/
├── prd.md                              # Requirements (source of truth)
├── README.md
├── .specify/
│   ├── memory/constitution.md          # Dos/don'ts
│   ├── templates/                      # spec, plan, tasks templates
│   ├── scripts/bash/                   # Used by slash commands
│   └── integration.json
├── .cursor/skills/                     # 5 core slash commands only
│   ├── speckit-constitution/
│   ├── speckit-specify/
│   ├── speckit-plan/
│   ├── speckit-tasks/
│   └── speckit-implement/
└── specs/                              # Created by /speckit-specify (not yet)
    └── 001-gold-alert/
        ├── spec.md
        ├── plan.md
        └── tasks.md
```

App code (`src/`, `app.py`, `tests/`, `.github/workflows/`) is added during `/speckit-implement`.

### Workflow (5 steps)

Run **in order** in Cursor Agent:

```
1. /speckit-constitution   → Done (.specify/memory/constitution.md)
2. /speckit-specify        → Create spec from prd.md
3. /speckit-plan           → Technical plan
4. /speckit-tasks          → Task breakdown
5. /speckit-implement      → Build code (TDD)
```

**Gate:** Approve `spec.md`, `plan.md`, and `tasks.md` before `/speckit-implement`.

### Next command

```
/speckit-specify Build the Gold trailing-low alert engine from prd.md.
SnapDeploy hosting + GitHub Actions 08:30 IST trigger. What/why only.
```

### Re-init Spec Kit (restores full scaffold)

```bash
uvx --from git+https://github.com/github/spec-kit.git specify init --here --integration cursor-agent --force
```

Note: re-init adds optional skills/workflows back. Remove them again if you prefer this lean layout.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (for Spec Kit CLI)
- Cursor Agent

### Secrets

Copy `.env.example` → `.env` locally (never commit `.env`). Production secrets go in SnapDeploy env vars.
