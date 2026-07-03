# Gold Price Alert Constitution

Governing principles for all spec-driven development on this repository.  
**Supersedes** ad-hoc AI prompts. On conflict with `prd.md`, **stop and ask the product owner** before proceeding.

---

## Core Principles

### I. Spec-Driven, PRD-Grounded

Every feature follows the Spec Kit workflow: **Constitution → Specify → Plan → Tasks → Implement**.  
Functional requirements live in `prd.md` (locked decisions). Generated artifacts live under `specs/`.  
If `spec.md`, `plan.md`, or code **conflicts with `prd.md`**, the agent **MUST pause and ask** — do not silently override.

### II. Strict Test-Driven Development (NON-NEGOTIABLE)

**Red → Green → Refactor** for all core logic (fetcher, analyzer, notifier, templates).

- Write failing tests **before** implementation.
- Do not mark tasks complete until tests pass.
- Prioritize: trading-day window math, top-down short-circuit, fallback vs full mode routing, template rendering.

### III. Minimal, Typed Python

- Plain modules matching `prd.md` layout (`fetcher`, `analyzer`, `notifier`, `config`, `templates`).
- **Type hints** on public functions; small focused functions.
- **Smallest correct diff** — no drive-by refactors or unrelated changes.
- **Self-explanatory code** — no verbose comments; only comment non-obvious market/business rules.

### IV. Scope Discipline

**In v1 (from `prd.md`):** headless cron, GC=F, trailing-low breach detection, **daily gold report** (HTML Email + WhatsApp), fallback/hard-failure handling.

The agent **MAY propose** improvements outside `prd.md` but **MUST NOT implement** them without explicit owner approval.

**Out of scope unless approved:** UI, database, multi-asset, alert deduplication, backtesting, new notification channels.

### V. Secrets, Privacy & Observability

- **DO:** load credentials from environment / `.env` (gitignored).
- **DO:** maintain `.env.example` documenting every required variable.
- **DON'T:** hardcode SMTP passwords, Twilio tokens, or API keys.
- **DON'T:** log secrets, tokens, or full notification bodies containing PII.
- **DO:** structured logs for fetch status, mode (full/fallback/hard-fail), window evaluated, alert sent/skipped.

### VI. Notification Contract

| Event | Email | WhatsApp |
|---|---|---|
| Daily gold report (every successful fetch) | ✅ Required (HTML + plain) | ✅ Required (plain text) |
| Breach highlight in daily report | ✅ Same message | ✅ Same message |
| Fallback / degraded data notice | ✅ Required (HTML + plain) | ❌ No |
| Hard failure (`CRITICAL_DATA_FETCH_ERROR`) | ✅ Required (HTML + plain) | ❌ No |

Message content must follow daily report and system templates in `prd.md` Section 5. Breach detection horizons remain Section 3.2 trading-day windows.

### VII. Market Logic Integrity

- Window sizes use **standard US trading days**: 252, 126, 63, 21, 15, 10 — **not** calendar-day counts.
- Evaluation order: **top-down short-circuit** (252 → 126 → 63 → 21 → 15 → 10); first match wins.
- Fetch target: `period="1y"` (~252 rows); full mode ≥252 days; fallback 10–251; hard fail <10.
- Schedule: **08:30 IST** daily.

---

## Engineering Constraints

| Area | Rule |
|---|---|
| **Language** | Python 3.11+ |
| **Data** | `yfinance` for GC=F; `pandas` for window ops |
| **Email** | Gmail SMTP (`smtp.gmail.com:465`, SSL) |
| **WhatsApp** | Twilio API (required for price alerts) |
| **Deployment** | **[SnapDeploy](https://snapdeploy.dev)** — free tier, GitHub-connected container, auto-sleep/wake |
| **Schedule trigger** | GitHub Actions cron → HTTP `POST /run` at **08:30 IST** (1 wake/day) |
| **Dependencies** | Pin versions in `requirements.txt` |
| **Git commits** | **Never commit unless the owner explicitly asks** |

### SnapDeploy constraints (v1)

- Free tier: up to **4 containers**, **512 MB RAM**, **0.25 vCPU**, **10 wake-ups/deploys per day** — this app uses **1/day**.
- **No credit card** required for free tier.
- Secrets live in **SnapDeploy env vars** (+ GitHub Actions secrets for `CRON_SECRET` and app URL).
- SnapDeploy does **not** provide native cron — GitHub Actions is the scheduler; SnapDeploy is the runtime.

---

## Development Workflow

1. Read `prd.md` and this constitution before any implementation.
2. Run `/speckit-specify` → `/speckit-plan` → `/speckit-tasks`; owner approves each gate.
3. `/speckit-implement` executes approved tasks only.
4. Tests must pass before claiming done.
5. Update README when SnapDeploy setup or GitHub Actions schedule changes.

### Quality gates before merge (when owner requests commit)

- [ ] All acceptance criteria in `prd.md` Section 9 addressed
- [ ] Unit tests pass (`pytest`)
- [ ] No secrets in diff
- [ ] `.env.example` complete

---

## Governance

- This constitution amends via `/speckit-constitution` with owner approval.
- `prd.md` locked decisions (Section 11) require owner approval to change.
- Complexity beyond `prd.md` must be justified in `plan.md` before implementation.

**Version**: 1.2.0 | **Ratified**: 2026-07-03 | **Last Amended**: 2026-07-03 (daily HTML reports)
