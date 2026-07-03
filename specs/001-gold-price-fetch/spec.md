# Feature Specification: Gold Price Fetch Utility

**Feature Branch**: `001-gold-price-fetch`

**Created**: 2026-07-03

**Status**: Draft

**Input**: Utility module setup and market-data integration to fetch Gold Futures (`GC=F`) daily closing prices for the alert engine.

**PRD traceability**: `prd.md` §3.1 (FR-01–FR-05, FR-05a), §4 NFR-01 (fetch resilience only)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve full year of gold closes (Priority: P1)

The alert engine needs a reliable daily history of Gold Futures closing prices so downstream logic can evaluate 1-year trailing lows. An operator invokes the fetch utility once per run and receives a ordered series of **trading-day closes** covering approximately one calendar year (~252 sessions).

**Why this priority**: Without price history, no alert can fire. This is the foundation of the entire product.

**Independent Test**: Run the fetch utility when the market data provider is healthy; verify the result contains ≥252 valid daily closes for `GC=F`, each with a date and numeric close, ordered oldest → newest.

**Acceptance Scenarios**:

1. **Given** the market data provider is reachable, **When** the fetch utility runs, **Then** it returns a series with **≥252 trading days** of closing prices and marks the run as **full mode**.
2. **Given** a successful full fetch, **When** the result is inspected, **Then** each row represents one **trading session** (no weekend/holiday filler rows with invalid closes).
3. **Given** a successful fetch, **When** the latest row is read, **Then** it represents the **most recent trading day's close** (today's `P_current` candidate).

---

### User Story 2 - Survive transient provider failures (Priority: P2)

Network blips or temporary Yahoo Finance outages must not immediately abort the daily run. The utility retries before giving up.

**Why this priority**: A single timeout should not skip a trading day's alert evaluation.

**Independent Test**: Simulate two failed attempts followed by a successful response; verify the utility succeeds without surfacing a hard failure.

**Acceptance Scenarios**:

1. **Given** the first fetch attempt fails (timeout or empty response), **When** the utility retries up to **3 times** with **60 seconds** between attempts, **Then** a successful attempt on retry 2 or 3 returns valid data without hard failure.
2. **Given** all 3 attempts fail or return unusable data, **When** the utility completes, **Then** it returns **hard failure** with error type `CRITICAL_DATA_FETCH_ERROR` and **zero** price rows suitable for analysis.

---

### User Story 3 - Degraded history fallback (Priority: P3)

When the provider returns partial history (enough for shorter windows but not a full year), the utility must still return usable data and clearly signal **fallback mode** so downstream components can skip ineligible windows.

**Why this priority**: Partial data is better than no data; the PRD allows analysis on 10–251 trading days.

**Independent Test**: Simulate a response with exactly 180 trading days; verify fallback mode is set and 180 valid closes are returned.

**Acceptance Scenarios**:

1. **Given** the provider returns **10–251** valid trading days after retries, **When** the utility completes, **Then** it marks **fallback mode**, returns all available closes, and records the count (e.g. `received=180, expected=252`).
2. **Given** the provider returns **fewer than 10** valid trading days, **When** the utility completes, **Then** it marks **hard failure** (`CRITICAL_DATA_FETCH_ERROR`) and returns no analyzable series.

---

### Edge Cases

- Provider returns rows with missing or non-numeric close values → exclude invalid rows; count only valid trading days.
- Provider returns duplicate dates → keep one row per date (most recent fetch wins).
- Provider returns exactly 252 rows but some are invalid → count valid rows only for mode classification.
- Fetch succeeds on retry 3 after ~120 seconds total wait → still valid; must complete within retry budget.
- Market holiday: latest row is previous session's close (expected — no synthetic "today" row on non-trading days).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The utility MUST fetch daily **closing prices** for **Gold Futures ticker `GC=F`** from **Yahoo Finance** as the **sole** pricing source (`prd.md` FR-01).
- **FR-002**: The utility MUST request approximately **one calendar year** of history, targeting **~252 trading days** — not 365 calendar days (`prd.md` FR-02, D10).
- **FR-003**: Each returned row MUST represent one **trading day** with a **valid numeric close**; weekends and exchange holidays are excluded implicitly (`prd.md` FR-04).
- **FR-004**: The utility MUST classify each run into exactly one **fetch mode**:
  - **Full**: ≥252 valid trading days
  - **Fallback**: 10–251 valid trading days
  - **Hard failure**: 0–9 valid trading days or total fetch failure after retries
- **FR-005**: On hard failure, the utility MUST expose error type **`CRITICAL_DATA_FETCH_ERROR`** for downstream alerting (`prd.md` FR-05a).
- **FR-006**: On fallback mode, the utility MUST expose **`DATA_FETCH_DEGRADED`** metadata including `received` and `expected=252` counts (`prd.md` §3.1.1).
- **FR-007**: The utility MUST retry failed or empty fetches up to **3 times** with **60-second** delay between attempts (`prd.md` NFR-01).
- **FR-008**: The utility MUST return closes ordered **oldest → newest**, with the **last row** being the most recent trading session.
- **FR-009**: The utility MUST NOT perform low-detection, notifications, or scheduling — **fetch only** (single responsibility).
- **FR-010**: The utility MUST NOT require SMTP, Twilio, or deployment credentials — market data fetch only.

### Key Entities

- **TradingDayClose**: One session's closing price — attributes: `date` (trading date), `close` (USD price, positive number).
- **FetchResult**: Outcome of one fetch run — attributes: `mode` (`full` | `fallback` | `hard_failure`), `trading_days` (count), `closes` (ordered list of `TradingDayClose`), `error_code` (nullable, e.g. `CRITICAL_DATA_FETCH_ERROR`), `degraded_code` (nullable, e.g. `DATA_FETCH_DEGRADED`).
- **RetryPolicy**: Implicit behavior — max 3 attempts, 60s delay, no user configuration required in v1.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When the market data provider is healthy, **100%** of fetch runs return ≥252 valid trading-day closes classified as **full mode**.
- **SC-002**: When the provider fails twice then succeeds, the utility completes successfully **without** hard failure in **≥95%** of simulated transient-failure tests.
- **SC-003**: When partial data (10–251 days) is returned, the utility correctly classifies **fallback mode** and preserves **100%** of valid rows.
- **SC-004**: When data is unusable (<10 days or all retries fail), hard failure is reported **100%** of the time with `CRITICAL_DATA_FETCH_ERROR`.
- **SC-005**: A complete fetch run (including retries) finishes within **5 minutes** under normal network conditions.
- **SC-006**: Fetch utility can be invoked independently and its result inspected without running alert or notification logic.

---

## Assumptions

- Yahoo Finance public data for `GC=F` remains available without API keys for v1.
- One calendar year of daily data (~252 trading rows) is sufficient for all trailing windows per `prd.md`.
- Downstream analyzer (separate feature) consumes `FetchResult` — this feature does not compute lows.
- Tests use mocked provider responses for edge cases; one optional integration test may hit live Yahoo Finance manually.
- TDD applies: tests for mode classification and retry behavior are written **before** implementation (constitution §II).

---

## Out of Scope (this feature)

- Trailing-low detection / short-circuit logic
- Email, WhatsApp, or failure notifications
- SnapDeploy `/run` HTTP endpoint
- GitHub Actions scheduling
- Multi-asset or alternate tickers
- Persistent storage / database caching of price history

---

## Dependencies

- `prd.md` locked decisions D8, D10 (fallback thresholds, trading-day windows)
- `.specify/memory/constitution.md` §II (TDD), §V (no secret logging)
