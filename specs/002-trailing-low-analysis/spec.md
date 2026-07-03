# Feature Specification: Trailing-Low Analysis & Service Layer

**Feature Branch**: `002-trailing-low-analysis`

**Created**: 2026-07-03

**Status**: Implemented (spec backfilled)

**Input**: Analyzer + orchestration service that evaluates GC=F trailing lows top-down and prepares alert-ready results with optional INR parity.

**PRD traceability**: `prd.md` §3.2 (FR-06–FR-12), §3.4 (FR-27–FR-30), §9 AC-13

**Depends on**: `001-gold-price-fetch` (`FetchResult`, `TradingDayClose`)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect longest eligible trailing low (Priority: P1)

When the daily run has usable price history, the engine must determine whether today's close is at or below the minimum of any trailing window — and return **only the longest window that triggers**.

**Why this priority**: This is the core product signal; without it, no price alert can fire.

**Independent Test**: Feed a synthetic series of 252 descending closes where today is the window minimum → `analyze_lows()` returns a `WindowBreach` with `window_key="1y"`.

**Acceptance Scenarios**:

1. **Given** ≥252 trading days in full mode, **When** `P_current <= min(last 252 closes)`, **Then** analysis returns breach for **1y** (N=252) and does not evaluate shorter windows.
2. **Given** today's close is **not** the minimum in any eligible window, **When** analysis runs top-down, **Then** it evaluates **every eligible window** (252 through 10), returns `None` for breach — **daily report still sent by pipeline** (not silent exit).
3. **Given** 1y returns **no** but 6m would return **yes**, **When** analysis runs, **Then** it continues past 1y and returns the **6m** breach.
4. **Given** today's close **ties** the window minimum, **When** analysis runs, **Then** that window **still triggers** (`<=` per PRD).

---

### User Story 2 - Respect fallback window eligibility (Priority: P2)

When fetch returns partial history (10–251 days), analysis must skip windows where `N > available_trading_days` but still evaluate eligible shorter horizons top-down.

**Why this priority**: Fallback mode is a locked PRD behavior; incorrect skipping would miss valid alerts or false-positive on ineligible windows.

**Independent Test**: Feed 180 monotonic-descending closes → breach at **6m** (126), not 1y.

**Acceptance Scenarios**:

1. **Given** fallback mode with 180 trading days, **When** analysis runs top-down, **Then** windows 252 and 126 are skipped if ineligible, and the **first eligible** triggering window wins.
2. **Given** hard failure (<10 days), **When** the service runs, **Then** analysis is **skipped** entirely.

---

### User Story 3 - Orchestrate fetch, analysis, and India display quote (Priority: P3)

A service layer must compose fetch → analyze → **IndiaGoldQuote** for downstream daily templates/notifier.

**Why this priority**: Separates orchestration from pure window math; enables mocked end-to-end unit tests without network.

**Independent Test**: Mock fetch returning closes and mock INR rate → `GoldAlertService.run()` returns `RunResult` with `india_quote` set (breach or not).

**Acceptance Scenarios**:

1. **Given** successful fetch and successful `INR=X`, **When** `GoldAlertService.run()` completes, **Then** `RunResult.india_quote` is non-null and `inr_line` property returns formatted summary text.
2. **Given** successful fetch and failed `INR=X`, **When** service runs, **Then** `india_quote is None` — daily report uses USD only.
3. **Given** no breach, **When** service runs, **Then** INR is **still fetched** for daily report display.
4. **Given** hard failure, **When** service runs, **Then** analysis skipped and `india_quote is None`.

---

### User Story 4 - Full window scan for daily report (Priority: P2)

`evaluate_windows()` evaluates **all** six horizons (no short-circuit) for the daily report window scan table.

**Acceptance Scenarios**:

1. **Given** 252 closes, **When** `evaluate_windows()` runs, **Then** returns six `WindowEvaluation` rows with min, date, and `is_lowest` flag.
2. **Given** fallback with 180 days, **When** evaluated, **Then** ineligible windows have `skipped=True`.
3. **Given** 1y breach via `analyze_lows()`, **When** `evaluate_windows()` runs, **Then** multiple rows may show `is_lowest=True` (informational only).

---

### Edge Cases

- Exactly 10 trading days → only 10d window eligible.
- Today equals window min but prior days had lower values excluded from min calc → `previous_min` is min of window **excluding today**.
- Hard failure empty closes → service returns without calling analyzer logic on prices.
- Monotonic series where multiple windows would trigger mathematically → only longest (top-down short-circuit) is returned.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Analyzer MUST evaluate windows in order **252 → 126 → 63 → 21 → 15 → 10** (`prd.md` FR-06).
- **FR-002**: On **yes**, analyzer MUST **short-circuit** — lower windows MUST NOT be evaluated (`prd.md` FR-07).
- **FR-002a**: On **no**, analyzer MUST continue to the **next shorter** eligible window (`prd.md` FR-06, FR-08).
- **FR-002b**: On **no for all** eligible windows, `analyze_lows()` MUST return `None` (no breach). Pipeline still sends daily report.
- **FR-003**: Trigger condition MUST be `P_current <= min(Window(N))` including ties (`prd.md` §3.2).
- **FR-004**: Analyzer MUST skip windows where `N > len(closes)` in `analyze_lows()` (`prd.md` fallback rules).
- **FR-005**: Breach MUST include `current` (`P_current`) and `previous_min` = min of window **excluding today** (`prd.md` FR-11).
- **FR-006**: Service MUST skip analysis on `FetchMode.HARD_FAILURE` (`prd.md` FR-05a).
- **FR-007**: Service MUST fetch INR rate on **every successful run**; failure MUST NOT suppress daily report (`prd.md` FR-28, FR-30).
- **FR-008**: `RunResult.should_alert` MUST be `True` iff not hard failure **and** breach is not `None` (gates breach-specific copy, not notification dispatch).
- **FR-009**: `evaluate_windows()` MUST evaluate all six windows without short-circuit for display in daily report.

### Key Entities

- **`WindowBreach`**: One triggered horizon — key, label, N, current, previous_min.
- **`WindowEvaluation`**: Scan row — key, label, N, window_min, min_date, is_lowest, skipped.
- **`AnalysisResult`**: Wraps optional breach.
- **`RunResult`**: Fetch + analysis + optional `india_quote`; `inr_line` property for plain-text summary.

---

## Success Criteria *(mandatory)*

- **SC-001**: 100% of PRD window-order unit tests pass with synthetic closes.
- **SC-002**: Service unit tests pass with injected fetch/INR mocks (no network).
- **SC-003**: `analyze_lows()` completes in <10ms on 252 rows (in-memory).
- **SC-004**: Public API documented in `contracts/` matches implemented signatures.

## Assumptions

- Fetch module from `001` is stable; `closes[-1]` is always `P_current`.
- INR conversion reuses `src/pricing.py` from feature 001 pricing work.
- Notification templates and dispatch are **out of scope** for this feature (feature 003+).
