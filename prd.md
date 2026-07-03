# Product Requirements Document (PRD)

> **AI Implementation Brief** — This document is structured for autonomous implementation. Read sections in order: Context → Requirements → Acceptance Criteria → Architecture → Locked Decisions.

---

## Document Metadata

| Field | Value |
|---|---|
| **Project** | Trailing Historical Lows — Automated Gold Alert Engine |
| **Repository** | `gold-price-alert` |
| **Status** | Ready for Implementation |
| **Deployment** | [SnapDeploy](https://snapdeploy.dev) — container hosting from GitHub (free tier) |
| **Primary Language** | Python 3.x |
| **Last Updated** | 2026-07-03 |
| **Schedule** | **Morning IST** — recommended cron: `30 8 * * *` (08:30 IST daily) |

---

## 1. Problem Statement

Track the daily closing price of Gold and automatically notify the user when **today's close is the lowest** in a trailing lookback window. The engine checks horizons **top-down** (1 year first, then shorter) and sends **one specific alert** for the **longest window that triggers** — lower windows are not evaluated once a higher window matches.

---

## 2. Scope

### In Scope

- Daily fetch of Gold Futures closing price (`GC=F` via Yahoo Finance)
- Top-down low-detection with **short-circuit** (first matching window wins; do not evaluate lower windows)
- **Both Email and WhatsApp** alerts on every price trigger (v1)
- Window-specific message templates (e.g. *"Today is the lowest in the last 1 year"*)
- Retry logic, logging, secure credential handling
- **Failure email** on hard fetch failure (`CRITICAL_DATA_FETCH_ERROR`)
- **Fallback mode:** if API returns 10–251 trading days, analyze available recent days and **Email** a degraded-data warning
- Cron-compatible single-run script (run once, exit)
- **SnapDeploy** deployment: GitHub-connected container, auto-sleep/wake, daily scheduled trigger
- **India display pricing:** USD `GC=F` for detection; **INR per 10g parity** in alert text via `GC=F` + `INR=X` (no MCX ticker, no paid APIs)

### Out of Scope

- Web UI, dashboard, or mobile app
- Real-time intraday alerts (daily close only)
- Multi-asset support (Gold only for v1)
- MCX Gold futures ticker or Indian exchange-native low detection
- GoldAPI.io, MetalpriceAPI, or other API-key precious-metal services
- Exact retail jeweler billing (import duty, GST, making charges)
- Historical alert storage / database
- Alert deduplication across consecutive days
- Backtesting UI

---

## 3. Functional Requirements

### 3.1 Data Fetching

| ID | Requirement |
|---|---|
| **FR-01** | Track **Gold Futures** ticker `GC=F` on Yahoo Finance as the **sole pricing source for low-detection** (trailing windows, triggers). |
| **FR-02** | Fetch **~1 calendar year** of daily closes using `period="1y"` (yfinance returns **~252 trading rows** for GC=F). This matches the 1-Year window (N=252). Do **not** require 365 rows — markets have ~252 trading days per calendar year. |
| **FR-03** | Execute **once per day in the morning (IST)** — **08:30 IST** (`30 8 * * *` with `TZ=Asia/Kolkata`). GC=F settles ~02:30–03:30 IST; 08:30 IST ensures data is available. |
| **FR-04** | Windows are built from **trading days only** (rows with valid close prices). Weekends and exchange holidays are excluded implicitly — each row is one session close. |
| **FR-05** | **Primary target:** receive **≥252 trading days** (full mode). If the API returns **10–251 trading days** after retries → **fallback mode** (Section 3.1.1): use available recent days, skip windows that exceed available history, and send an **Email** degraded-data alert. |
| **FR-05a** | If the API returns **zero data** or **fewer than 10** trading days after retries → **hard failure**: log `CRITICAL_DATA_FETCH_ERROR`, send **Email** alert (Section 5.3), exit without low-detection. |

### 3.1.2 Deployment & Scheduling (SnapDeploy)

| ID | Requirement |
|---|---|
| **FR-19** | **Host on SnapDeploy** (free tier): connect this GitHub repo; SnapDeploy auto-builds the Python container (no manual Dockerfile required unless needed). |
| **FR-20** | Container spec: **512 MB RAM / 0.25 vCPU** is sufficient; script runs once daily (~seconds of CPU). |
| **FR-21** | **Auto-sleep / auto-wake:** container sleeps when idle; wakes on incoming HTTP (~60s cold start acceptable before 08:30 IST run). |
| **FR-22** | Expose a **protected HTTP trigger** (e.g. `POST /run` with `CRON_SECRET` header or query param) that invokes the alert pipeline once and returns JSON status. No public UI beyond health + run endpoints. |
| **FR-23** | **Daily schedule at 08:30 IST** via **GitHub Actions** cron workflow (SnapDeploy has no built-in cron): workflow sends one authenticated HTTP request to the SnapDeploy app URL → wakes container → runs job → container sleeps again. |
| **FR-24** | **Free-tier budget:** 1 wake/run per day (well within SnapDeploy's **10 deploys/wake-ups per day** limit). |
| **FR-25** | Store all secrets (SMTP, Twilio, `CRON_SECRET`) in **SnapDeploy environment variables** dashboard — not in git. |
| **FR-26** | Optional: `GET /health` for SnapDeploy health checks and manual smoke tests. |

#### 3.1.1 Fallback Mode (Partial / Degraded Data)

When Yahoo Finance returns incomplete history (<252 trading days) but enough recent days to evaluate at least the **10-day** window:

| Step | Behavior |
|---|---|
| 1 | Log `DATA_FETCH_DEGRADED` with count of trading days received (e.g. `received=180, expected=252`). |
| 2 | Send **Email-only** fallback alert (Section 5.4) — informs user that analysis runs on available recent days only. |
| 3 | Proceed with low-detection using **only the recent days returned**. |
| 4 | Evaluate windows **top-down** from the longest eligible horizon; **stop at the first trigger** (Section 3.2). |
| 5 | If that window triggers → send **one** window-specific price alert via **Email + WhatsApp** (Section 5.1), with a fallback note if degraded data was used. |

**Minimum data to run fallback:** **10 trading days** (shortest window). Below that → hard failure (FR-05a).

### 3.2 Low-Detection Logic

> **Design note — Trading days vs calendar days:** A "1-year" lookback in financial markets is **~252 trading sessions**, not 365 calendar days. Using N=365 would cause yfinance's `period="1y"` (~252 rows) to always miss the threshold and trigger fallback mode daily. Window sizes below use **standard US market trading-day equivalents** for each labeled horizon.

For each run, let:

- `P_current` = today's closing price (most recent trading day's close)
- `Window(N)` = the last **N trading days** of closing prices, **including** today

**Trigger condition** (per window):

```
P_current <= min(Window(N))
```

In plain language: **if today's close is the lowest (or tied for lowest) in the last N trading days, that window triggers.**

**Evaluation rules (one-line):**

| Result on window | Action |
|---|---|
| **No** (today is above the window low) | Try the **next shorter** window |
| **Yes** (today is at or below the window low) | Send **one alert** for that window and **stop** |
| **No on all** eligible windows | **No alert** — silent exit |

```text
252 (1y) ──no──► 126 (6m) ──no──► 63 (3m) ──no──► 21 (1m) ──no──► 15 (15d) ──no──► 10 (10d) ──no──► silent exit
252 (1y) ──yes──► alert (1y) & STOP   (6m … 10d are NOT evaluated)
```

> **Important:** Short-circuit applies only on **yes**. A **no** on 1-Year does **not** exit — it continues to 6-Month, then 3-Month, and so on until a window triggers or all are exhausted.

| Evaluation Order | Window Label | N (Trading Days) | ~Calendar Equivalent | Message Key |
|---|---|---|---|---|
| 1 | 1-Year | **252** | ~1 calendar year | `1y` |
| 2 | 6-Month | **126** | ~6 calendar months | `6m` |
| 3 | 3-Month | **63** | ~3 calendar months | `3m` |
| 4 | 1-Month | **21** | ~1 calendar month | `1m` |
| 5 | 15-Day | **15** | ~3 calendar weeks | `15d` |
| 6 | 10-Day | **10** | ~2 calendar weeks | `10d` |

**Top-down short-circuit rules:**

| ID | Requirement |
|---|---|
| **FR-06** | Evaluate windows in **top-down order**: 252 → 126 → 63 → 21 → 15 → 10. Skip windows where `N > available_trading_days` (fallback mode). On **no**, continue to the next shorter window. |
| **FR-07** | **Short-circuit on yes only:** as soon as the **first (longest eligible) window** triggers, **stop** — do **not** evaluate or alert on any lower/shorter windows. A **no** must **not** stop evaluation. |
| **FR-08** | If **no** on every eligible window after the full top-down pass → log locally and **exit silently** (no user notification). |
| **FR-09** | If a window triggers → send **exactly one** alert using **that window's specific template** (Section 5.1). Never bundle multiple windows in one message. |
| **FR-10** | Example: if 1-Year triggers, send the 1-Year email/WhatsApp only — even though 10-Day would also be true mathematically, **do not check 10-Day**. |
| **FR-11** | Include **Previous min** = `min(Window(N) excluding today)` and **Current** = `P_current` in the alert. |
| **FR-12** | Re-alert **every day** the condition holds — no deduplication in v1. |

### 3.3 Notifications

| ID | Requirement |
|---|---|
| **FR-13** | **Email (SMTP) is required** for v1 — every price alert, fallback warning, and hard failure alert. |
| **FR-14** | **WhatsApp (Twilio) is required** for v1 — **price alerts only** (not failure/fallback system alerts). |
| **FR-15** | Dispatch **Email + WhatsApp** on price alerts; dispatch **Email only** on fallback and hard failure alerts. |
| **FR-16** | Recipient addresses must be configurable via environment variables (not hardcoded). |
| **FR-17** | On **hard fetch failure** (`CRITICAL_DATA_FETCH_ERROR`), send a dedicated **Email** failure notification (Section 5.3). |
| **FR-18** | On **fallback mode** (partial data), send a dedicated **Email** degraded-data notification (Section 5.4) before running eligible windows. |

### 3.4 India Display Pricing (Alert Text Only)

> **Detection vs display:** Trailing-low logic runs **100% on `GC=F` USD closes**. India INR lines are **informational only** — they do **not** affect triggers, windows, or short-circuit order.

| ID | Requirement |
|---|---|
| **FR-27** | Use **`src/pricing.py`** to convert USD gold to **INR per 10 grams** for alert messages when `INR=X` is available. |
| **FR-28** | Fetch **`INR=X`** (USD/INR) via yfinance — **no API keys**; used only at notification time, not for window math. |
| **FR-29** | Conversion formula: `(gold_usd_per_troy_oz / 31.1035) × 10 × usd_inr_rate` — international **24K parity**, not retail shop price. |
| **FR-30** | If `INR=X` fetch fails → send alert with **USD only**; do **not** fail the run or skip the price alert. |
| **FR-31** | Alert body must label INR as **parity** and note exclusion of import duty, GST, and local premium (Section 5.1). |
| **FR-32** | Do **not** use MCX tickers, GoldAPI, or MetalpriceAPI in v1. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| **NFR-01** | **Data fetch resilience:** Retry up to **3 times** with **60-second** delay. After retries: (a) **≥252 trading days** → full run; (b) **10–251 trading days** → fallback mode (Section 3.1.1) + Email alert; (c) **<10 days or empty** → hard failure: log `CRITICAL_DATA_FETCH_ERROR`, Email alert, exit. |
| **NFR-02** | **Security:** No plaintext credentials in source code. All secrets via environment variables or `.env` (gitignored). |
| **NFR-03** | **Logging:** Write structured logs on every run (fetch status, windows evaluated top-down, alerts sent/skipped, failures). |
| **NFR-04** | **Daily re-alerts:** Same lows triggering on consecutive days must alert again each day. |
| **NFR-05** | **Dependencies:** Pin versions in `requirements.txt`. |
| **NFR-06** | **Timezone:** Cron and timestamps in user-facing messages use **IST (`Asia/Kolkata`)** unless noted otherwise. |

---

## 5. Notification Payload Schema

### 5.1 Window-Specific Templates (Price Alerts)

When **one window triggers** (short-circuit — only the longest matching horizon), send **one message** using that window's template.

| Window | Subject | Body |
|---|---|---|
| **1-Year** | `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 1 year` | See body format below |
| **6-Month** | `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 6 months` | See body format below |
| **3-Month** | `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 3 months` | See body format below |
| **1-Month** | `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 1 month` | See body format below |
| **15-Day** | `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 15 days` | See body format below |
| **10-Day** | `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 10 days` | See body format below |

**Body format** (substitute window-specific headline and values):

```
Gold trailing-low alert (GC=F)

📉 Today is the lowest Gold close (GC=F) in the last **<horizon>**.
Previous low: $<prev_min> → Today: $<current>
India parity: ₹<current_inr_per_10g> / 10g (24K international parity, excl. import duty, GST, local premium)

Timestamp: <YYYY-MM-DD HH:MM:SS IST>
Action: Evaluate current entry positions.
```

**INR line:** Omit if `INR=X` unavailable (FR-30). Computed via `src/pricing.py` from `$current`, `$prev_min`, and latest `INR=X` — **not** used for trigger logic.

### 5.2 Example (1-Year Trigger — Lower Windows Not Checked)

**Subject:** `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 1 year`

**Body:**

```
Gold trailing-low alert (GC=F)

📉 Today is the lowest Gold close (GC=F) in the last **1 year**.
Previous low: $1,952.00 → Today: $1,945.20
India parity: ₹1,11,450.00 / 10g (24K international parity, excl. import duty, GST, local premium)

Timestamp: 2026-07-03 08:30:15 IST
Action: Evaluate current entry positions.
```

*(6-Month through 10-Day are not evaluated because 1-Year already triggered.)*

### 5.3 Hard Failure Template (Email Only)

Sent via **Email** when the API returns no usable data after all retries (**<10 trading days** or empty response).

**Subject:**

```
⛔ GOLD ALERT ENGINE: CRITICAL_DATA_FETCH_ERROR
```

**Body:**

```
The Gold price alert engine could not fetch usable market data for GC=F.

Error: CRITICAL_DATA_FETCH_ERROR
Trading days received: <count>
Retries exhausted: 3 attempts with 60s delay
Timestamp: <YYYY-MM-DD HH:MM:SS IST>

No low-detection was performed. Investigate Yahoo Finance connectivity or ticker availability.
```

### 5.4 Fallback / Degraded Data Template (Email Only)

Sent via **Email** when the API returns **partial data** (10–251 trading days). Low-detection still runs on available recent days.

**Subject:**

```
⚠️ GOLD ALERT ENGINE: Running on Fallback Data (<count> days)
```

**Body:**

```
Yahoo Finance returned incomplete history for GC=F.

Expected: 252 trading days (~1 calendar year)
Received: <count> trading days
Mode: FALLBACK — using available recent days only
Skipped windows: <comma-separated list of windows not evaluated, e.g. 1-Year>
Timestamp: <YYYY-MM-DD HH:MM:SS IST>

Low-detection will proceed top-down for eligible windows (first match wins). A separate price alert follows if a window triggers.
```

**Price alert addendum** (append to Section 5.1 body when fallback was used):

```
⚠️ Note: This alert used fallback data (<count> trading days available, not full 252-day / 1-year history).
```

---

## 6. System Architecture

```
[GitHub Actions — 08:30 IST cron]
         │
         │  POST /run (CRON_SECRET) → SnapDeploy URL
         ▼
[SnapDeploy Container — auto-wake → run → auto-sleep]
         │
         │  Fetch GC=F (yfinance, 3 retries)
         ▼
         ├── <10 days or empty ──► CRITICAL_DATA_FETCH_ERROR → Email → exit
         │
         ├── 10–251 days ──► FALLBACK MODE → Email degraded alert
         │                    └── Top-down short-circuit (eligible windows)
         │
         └── ≥252 days ──► FULL MODE
                              └── Top-down short-circuit:
                                  252 → trigger? → alert & STOP
                                  else 126 → … → 10
                                       │
                                       ▼
                                 [Any trigger?]
                                  /           \
                                Yes            No
                                 │              │
                                 ▼              ▼
                          [One window-specific  [Log & exit
                           Email + WhatsApp      quietly]
                           for matched horizon]
```

### Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Market data | `yfinance` — `Ticker("GC=F").history(period="1y")` (~252 rows) |
| Data processing | `pandas` |
| Email | `smtplib` + Gmail SMTP (`smtp.gmail.com:465`, SSL) |
| WhatsApp | Twilio WhatsApp API (**required v1**) |
| Scheduling | GitHub Actions cron → HTTP wake of SnapDeploy container (08:30 IST) |
| Hosting | [SnapDeploy](https://snapdeploy.dev) free tier — GitHub deploy, auto-sleep/wake, no credit card |
| Config | SnapDeploy env vars + `python-dotenv` for local dev |

---

## 7. Suggested Project Structure

```
gold-price-alert/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── prd.md
├── app.py                # SnapDeploy entry: /health + protected /run → main.py
├── .github/
│   └── workflows/
│       └── daily-alert.yml   # 08:30 IST cron → POST SnapDeploy /run
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry: fetch → evaluate (top-down) → notify → log
│   ├── fetcher.py        # Yahoo pull, retry, full/fallback/hard-fail routing
│   ├── pricing.py        # GC=F USD → INR/10g for alert display (not detection)
│   ├── analyzer.py       # Top-down short-circuit: first trigger wins
│   ├── notifier.py       # Email + WhatsApp (price + failure alerts)
│   ├── templates.py      # Window-specific message templates
│   └── config.py         # Env loading and validation
└── tests/
    ├── test_analyzer.py
    └── test_notifier.py
```

---

## 8. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SMTP_HOST` | **Yes** | Default: `smtp.gmail.com` |
| `SMTP_PORT` | **Yes** | Default: `465` |
| `SMTP_USER` | **Yes** | Gmail address |
| `SMTP_PASSWORD` | **Yes** | Gmail 16-digit app password |
| `ALERT_EMAIL_TO` | **Yes** | Recipient email |
| `ALERT_EMAIL_FROM` | No | Defaults to `SMTP_USER` |
| `TWILIO_ACCOUNT_SID` | **Yes** | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | **Yes** | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | **Yes** | Twilio WhatsApp sender number |
| `TWILIO_WHATSAPP_TO` | **Yes** | User WhatsApp number |
| `TZ` | No | Default: `Asia/Kolkata` |
| `LOG_LEVEL` | No | Default: `INFO` |
| `CRON_SECRET` | **Yes** (SnapDeploy + GHA) | Shared secret for `/run` endpoint; set in SnapDeploy env + GitHub Actions secrets |
| `PORT` | No | Default: `8000` (SnapDeploy auto-detect) |

---

## 9. Acceptance Criteria

- [ ] **AC-01:** Fetches `GC=F` via `yfinance` with `period="1y"`; full mode when **≥252** trading rows; fallback when **10–251**.
- [ ] **AC-02:** Windows evaluated **top-down**: 252 → 126 → 63 → 21 → 15 → 10 (standard trading-day horizons).
- [ ] **AC-03:** Window triggers when today's close is the lowest in the last N **trading days** (inclusive).
- [ ] **AC-04:** Zero triggers → log and exit silently (no Email/WhatsApp).
- [ ] **AC-05:** Only **one window** may trigger per run — first match top-down; send **one** window-specific message (not a bundle).
- [ ] **AC-05a:** If 1-Year triggers, 6-Month through 10-Day must **not** be evaluated.
- [ ] **AC-06:** Every price alert sent via **both Email and WhatsApp**.
- [ ] **AC-07:** Same condition on consecutive days → alert sent again (no dedupe).
- [ ] **AC-08:** Hard failure (<10 days or empty after retries) → log `CRITICAL_DATA_FETCH_ERROR` + **Email** hard-failure alert; no low-detection.
- [ ] **AC-09:** Partial data (10–251 trading days) → **Email** fallback alert + low-detection on eligible windows only (skip windows where N > available days).
- [ ] **AC-09a:** Fallback price alerts include degraded-data note; still sent via Email + WhatsApp if windows trigger.
- [ ] **AC-10:** GitHub Actions workflow fires **daily at 08:30 IST** and hits SnapDeploy `/run` with `CRON_SECRET`.
- [ ] **AC-10a:** SnapDeploy container deploys from GitHub; env vars configured in dashboard; free-tier usage ≤1 wake/day.
- [ ] **AC-11:** No secrets in git; `.env.example` lists all required vars.
- [ ] **AC-12:** Unit tests cover short-circuit (1-Year blocks lower checks), single-window templates, no-trigger path, and failure path.
- [ ] **AC-13:** `pricing.py` converts GC=F USD + INR=X to INR/10g; unit tests pass; alerts omit INR line if INR=X fails.

---

## 10. Implementation Order (AI Agent)

1. **Scaffold** — `requirements.txt`, `src/` layout, `config.py`, `.env.example`
2. **Templates** — `templates.py` with six window templates + failure template + INR line via `pricing.py`
3. **Fetcher** — `fetcher.py` with `period="1y"`, retry, full (≥252) / fallback (10–251) / hard-fail routing
4. **Analyzer** — `analyzer.py` top-down short-circuit; returns at most one breach
5. **Notifier** — `notifier.py` Email + WhatsApp for price and failure alerts
6. **Main** — `main.py` orchestration, IST timestamps, logging
7. **Tests** — analyzer ordering + template rendering
8. **Docs** — README with SnapDeploy setup + GitHub Actions schedule
9. **Deploy** — `app.py` HTTP trigger, SnapDeploy connect, GHA workflow secrets
10. **Dry run** — manual `curl /run` against SnapDeploy URL; verify silent exit and failure paths

---

## 11. Locked Decisions (Product Owner — 2026-07-03)

| # | Decision |
|---|---|
| **D1** | **Email + WhatsApp both required** for v1 (no optional channel flag). |
| **D2** | Trigger = today's close is the **lowest in the last N trading days** — N values: **252, 126, 63, 21, 15, 10** (not calendar-day counts). |
| **D3** | Evaluation is **top-down**: 252 → 126 → 63 → 21 → 15 → 10. **No** → next window; **yes** → one alert and stop; **no on all** → silent exit. |
| **D4** | Send **one specific alert** for the matched window only (e.g. *"Today is the lowest in the last 1 year"*). Do not alert on lower windows when a higher window already triggered. |
| **D5** | Cron runs **morning IST** (recommended 08:30 IST). |
| **D6** | **Alert every day** the condition holds — no deduplication. |
| **D7** | On **hard failure** (<10 days or empty API) → log `CRITICAL_DATA_FETCH_ERROR` + **Email** alert; no analysis. |
| **D8** | On **partial data** (10–251 trading days) → **fallback to available recent days**, **Email** degraded alert, run eligible windows only (skip longer horizons). |
| **D9** | Price alerts (when windows trigger) → still **Email + WhatsApp**; include fallback note if degraded data was used. |
| **D10** | **Option A adopted:** window N values use **standard market trading days** (~252/year), not calendar days. Fetch `period="1y"` — do not require 365 rows. |
| **D11** | **SnapDeploy** is the v1 hosting platform: GitHub-connected container, free tier, auto-sleep/wake. Daily **08:30 IST** trigger via **GitHub Actions** → HTTP `/run`. No VPS/cron server management. |
| **D12** | **India pricing (Option 1):** Detection **100% on `GC=F` USD** trailing lows. Alert text adds **INR/10g parity** via `GC=F` + `INR=X` + `src/pricing.py`. No MCX, no paid metal APIs. INR failure → USD-only alert. |

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Trading day** | One exchange session with a valid close price; ~252 per calendar year for US markets |
| **Trailing window** | Last N **trading days** of closing prices, including today |
| **Trigger / breach** | `P_current <= min(Window(N))` — today is at or below the window low |
| **Top-down short-circuit** | Walk 252 → 126 → 63 → 21 → 15 → 10. **No** → continue; **yes** → alert that window and stop; **no on all** → no alert |
| **Previous min** | Minimum close in the window **excluding** today |
| **Headless** | No UI; daily job triggered via protected HTTP endpoint (not interactive) |
| **SnapDeploy** | Container host — GitHub deploy, auto-sleep when idle, wakes on HTTP traffic |
| **Fallback mode** | Partial API data (10–251 days): analyze recent days, skip ineligible windows, Email warning |
| **Hard failure** | Empty or <10 days after retries: no analysis, Email critical alert |
| **Full mode** | ≥252 trading days received — all six windows eligible |
| **Detection pricing** | `GC=F` USD closes only — triggers and windows |
| **Display pricing** | Optional INR/10g parity in alerts via `INR=X` + `pricing.py` — does not affect triggers |
| **INR parity** | International 24K equivalent per 10g; not retail jeweler price |
