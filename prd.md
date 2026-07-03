# Product Requirements Document (PRD)

> **AI Implementation Brief** — This document is structured for autonomous implementation. Read sections in order: Context → Requirements → Acceptance Criteria → Architecture → Locked Decisions.

---

## Document Metadata

| Field | Value |
|---|---|
| **Project** | Trailing Historical Lows — Automated Gold Alert Engine |
| **Repository** | `gold-price-alert` |
| **Status** | Ready for Implementation |
| **Deployment** | Cloud server, cron-triggered (headless — no UI) |
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
- **Fallback mode:** if API returns 10–364 trading days, analyze available recent days and **Email** a degraded-data warning
- Cron-compatible single-run script (run once, exit)

### Out of Scope

- Web UI, dashboard, or mobile app
- Real-time intraday alerts (daily close only)
- Multi-asset support (Gold only for v1)
- Historical alert storage / database
- Alert deduplication across consecutive days
- Backtesting UI

---

## 3. Functional Requirements

### 3.1 Data Fetching

| ID | Requirement |
|---|---|
| **FR-01** | Track **Gold Futures** ticker `GC=F` on Yahoo Finance as the sole pricing source. |
| **FR-02** | Fetch enough history to populate a **365 trading-day** window on each run. |
| **FR-03** | Execute **once per day in the morning (IST)** — recommended **08:30 IST** (`30 8 * * *` with `TZ=Asia/Kolkata`). |
| **FR-04** | Windows are built from **trading days** (rows with valid close prices). Weekends/holidays are skipped implicitly via available close data. |
| **FR-05** | **Primary target:** fetch **365 trading days**. If the API returns **fewer than 365 but ≥10** trading days after retries → enter **fallback mode** (Section 3.1.1): use available recent days, skip windows that exceed available history, and send an **Email** degraded-data alert. |
| **FR-05a** | If the API returns **zero data** or **fewer than 10** trading days after retries → **hard failure**: log `CRITICAL_DATA_FETCH_ERROR`, send **Email** alert (Section 5.3), exit without low-detection. |

#### 3.1.1 Fallback Mode (Partial / Degraded Data)

When Yahoo Finance returns incomplete history (<365 trading days) but enough recent days to evaluate at least the **10-day** window:

| Step | Behavior |
|---|---|
| 1 | Log `DATA_FETCH_DEGRADED` with count of trading days received (e.g. `received=180, expected=365`). |
| 2 | Send **Email-only** fallback alert (Section 5.4) — informs user that analysis runs on available recent days only. |
| 3 | Proceed with low-detection using **only the recent days returned**. |
| 4 | Evaluate windows **top-down** from the longest eligible horizon; **stop at the first trigger** (Section 3.2). |
| 5 | If that window triggers → send **one** window-specific price alert via **Email + WhatsApp** (Section 5.1), with a fallback note if degraded data was used. |

**Minimum data to run fallback:** **10 trading days** (shortest window). Below that → hard failure (FR-05a).

### 3.2 Low-Detection Logic

For each run, let:

- `P_current` = today's closing price (most recent trading day's close)
- `Window(N)` = the last **N trading days** of closing prices, **including** today

**Trigger condition** (per window):

```
P_current <= min(Window(N))
```

In plain language: **if today's close is the lowest (or tied for lowest) in the last N trading days, that window triggers.**

| Evaluation Order | Window Label | N (Trading Days) | Message Key |
|---|---|---|---|
| 1 | 1-Year | 365 | `1y` |
| 2 | 6-Month | 180 | `6m` |
| 3 | 3-Month | 90 | `3m` |
| 4 | 1-Month | 30 | `1m` |
| 5 | 15-Day | 15 | `15d` |
| 6 | 10-Day | 10 | `10d` |

**Top-down short-circuit rules:**

| ID | Requirement |
|---|---|
| **FR-06** | Evaluate windows in **top-down order**: 365 → 180 → 90 → 30 → 15 → 10. Skip windows where `N > available_trading_days` (fallback mode). |
| **FR-07** | **Short-circuit:** as soon as the **first (longest eligible) window** triggers, **stop** — do **not** evaluate or alert on any lower/shorter windows. |
| **FR-08** | If **no** window triggers after full top-down pass → log locally and **exit silently** (no user notification). |
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

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| **NFR-01** | **Data fetch resilience:** Retry up to **3 times** with **60-second** delay. After retries: (a) **≥365 days** → full run; (b) **10–364 days** → fallback mode (Section 3.1.1) + Email alert; (c) **<10 days or empty** → hard failure: log `CRITICAL_DATA_FETCH_ERROR`, Email alert, exit. |
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

Timestamp: <YYYY-MM-DD HH:MM:SS IST>
Action: Evaluate current entry positions.
```

### 5.2 Example (1-Year Trigger — Lower Windows Not Checked)

**Subject:** `🚨 GOLD ALERT: $1,945.20 — Today is the lowest in the last 1 year`

**Body:**

```
Gold trailing-low alert (GC=F)

📉 Today is the lowest Gold close (GC=F) in the last **1 year**.
Previous low: $1,952.00 → Today: $1,945.20

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

Sent via **Email** when the API returns **partial data** (10–364 trading days). Low-detection still runs on available recent days.

**Subject:**

```
⚠️ GOLD ALERT ENGINE: Running on Fallback Data (<count> days)
```

**Body:**

```
Yahoo Finance returned incomplete history for GC=F.

Expected: 365 trading days
Received: <count> trading days
Mode: FALLBACK — using available recent days only
Skipped windows: <comma-separated list of windows not evaluated, e.g. 1-Year>
Timestamp: <YYYY-MM-DD HH:MM:SS IST>

Low-detection will proceed top-down for eligible windows (first match wins). A separate price alert follows if a window triggers.
```

**Price alert addendum** (append to Section 5.1 body when fallback was used):

```
⚠️ Note: This alert used fallback data (<count> trading days available, not full 365-day history).
```

---

## 6. System Architecture

```
[Yahoo Finance / yfinance]
         │
         │  Pull daily closes (GC=F), 3 retries
         ▼
[Python Cron Script — morning IST]
         │
         ├── <10 days or empty ──► CRITICAL_DATA_FETCH_ERROR
         │                          └── Email (hard failure template) → exit
         │
         ├── 10–364 days ──► FALLBACK MODE
         │                    ├── Email (degraded-data template)
         │                    └── Top-down short-circuit on eligible windows only
         │
         └── ≥365 days ──► FULL MODE
                              └── Top-down short-circuit:
                                  365 → if trigger → alert & STOP
                                  else 180 → if trigger → alert & STOP
                                  else 90 → … → 10
                                       │
                                       ▼
                                 [Any trigger?]
                                  /           \
                                Yes            No
                                 │              │
                                 ▼              ▼
                          [One window-specific  [Log & exit
                           Email + WhatsApp      quietly]
                           for matched horizon
                           (+ fallback note
                            if degraded)]
```

### Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Market data | `yfinance` |
| Data processing | `pandas` |
| Email | `smtplib` + Gmail SMTP (`smtp.gmail.com:465`, SSL) |
| WhatsApp | Twilio WhatsApp API (**required v1**) |
| Scheduling | Cron with `TZ=Asia/Kolkata`, morning IST |
| Config | `python-dotenv` + environment variables |

---

## 7. Suggested Project Structure

```
gold-price-alert/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── prd.md
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry: fetch → evaluate (top-down) → notify → log
│   ├── fetcher.py        # Yahoo pull, retry, full/fallback/hard-fail routing
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

---

## 9. Acceptance Criteria

- [ ] **AC-01:** Fetches `GC=F` daily closes via `yfinance`; targets 365 trading days; accepts 10–364 for fallback mode.
- [ ] **AC-02:** Windows evaluated **top-down**: 365 → 180 → 90 → 30 → 15 → 10.
- [ ] **AC-03:** Window triggers when today's close is the lowest in the last N **trading days** (inclusive).
- [ ] **AC-04:** Zero triggers → log and exit silently (no Email/WhatsApp).
- [ ] **AC-05:** Only **one window** may trigger per run — first match top-down; send **one** window-specific message (not a bundle).
- [ ] **AC-05a:** If 1-Year triggers, 6-Month through 10-Day must **not** be evaluated.
- [ ] **AC-06:** Every price alert sent via **both Email and WhatsApp**.
- [ ] **AC-07:** Same condition on consecutive days → alert sent again (no dedupe).
- [ ] **AC-08:** Hard failure (<10 days or empty after retries) → log `CRITICAL_DATA_FETCH_ERROR` + **Email** hard-failure alert; no low-detection.
- [ ] **AC-09:** Partial data (10–364 trading days) → **Email** fallback alert + low-detection on eligible windows only (skip windows where N > available days).
- [ ] **AC-09a:** Fallback price alerts include degraded-data note; still sent via Email + WhatsApp if windows trigger.
- [ ] **AC-10:** Cron documented for **morning IST** (`30 8 * * *`, `TZ=Asia/Kolkata`).
- [ ] **AC-11:** No secrets in git; `.env.example` lists all required vars.
- [ ] **AC-12:** Unit tests cover short-circuit (1-Year blocks lower checks), single-window templates, no-trigger path, and failure path.

---

## 10. Implementation Order (AI Agent)

1. **Scaffold** — `requirements.txt`, `src/` layout, `config.py`, `.env.example`
2. **Templates** — `templates.py` with six window templates + failure template
3. **Fetcher** — `fetcher.py` with retry, full/fallback/hard-fail routing
4. **Analyzer** — `analyzer.py` top-down short-circuit; returns at most one breach
5. **Notifier** — `notifier.py` Email + WhatsApp for price and failure alerts
6. **Main** — `main.py` orchestration, IST timestamps, logging
7. **Tests** — analyzer ordering + template rendering
8. **Docs** — README with morning IST cron example
9. **Dry run** — manual execution; verify silent exit and failure notification paths

---

## 11. Locked Decisions (Product Owner — 2026-07-03)

| # | Decision |
|---|---|
| **D1** | **Email + WhatsApp both required** for v1 (no optional channel flag). |
| **D2** | Trigger = today's close is the **lowest in the last N trading days** (10, 15, 30, 90, 180, 365). |
| **D3** | Evaluation is **top-down with short-circuit**: 365 → 180 → 90 → 30 → 15 → 10; **stop at first trigger**. |
| **D4** | Send **one specific alert** for the matched window only (e.g. *"Today is the lowest in the last 1 year"*). Do not alert on lower windows when a higher window already triggered. |
| **D5** | Cron runs **morning IST** (recommended 08:30 IST). |
| **D6** | **Alert every day** the condition holds — no deduplication. |
| **D7** | On **hard failure** (<10 days or empty API) → log `CRITICAL_DATA_FETCH_ERROR` + **Email** alert; no analysis. |
| **D8** | On **partial data** (10–364 trading days) → **fallback to available recent days**, **Email** degraded alert, run eligible windows only (skip longer horizons). |
| **D9** | Price alerts (when windows trigger) → still **Email + WhatsApp**; include fallback note if degraded data was used. |

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Trailing window** | Last N **trading days** of closing prices, including today |
| **Trigger / breach** | `P_current <= min(Window(N))` — today is at or below the window low |
| **Top-down short-circuit** | Check longest window first; on first trigger, alert and stop — do not evaluate shorter windows |
| **Previous min** | Minimum close in the window **excluding** today |
| **Headless** | No UI; cron-invoked CLI script only |
| **Fallback mode** | Partial API data (10–364 days): analyze recent days, skip ineligible windows, Email warning |
| **Hard failure** | Empty or <10 days after retries: no analysis, Email critical alert |
