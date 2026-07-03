# Feature Specification: Daily HTML Alert Templates

**Feature Branch**: `003-alert-templates`

**Created**: 2026-07-03

**Status**: Implemented (rev 2 — daily HTML reports)

**Input**: Render PRD-compliant daily gold reports (HTML Email + plain text), hard failure, and fallback degraded data alerts.

**PRD traceability**: `prd.md` §5.1–§5.5 (FR-08–FR-09, FR-27–FR-33), §9 AC-12–AC-16

**Depends on**: `002-trailing-low-analysis` (`WindowBreach`, `WindowEvaluation`, `RunResult`), `src/pricing.py` (`IndiaGoldQuote`)

---

## User Scenarios & Testing

### User Story 1 - Daily gold report every successful run (Priority: P1)

When fetch succeeds (full or fallback), the user receives a **unified daily report** via Email (HTML) and WhatsApp (plain text) — whether or not a trailing-low breach occurred.

**Independent Test**: Given `breach=None` and valid closes, `render_daily_alert()` → subject `🪙 Gold Daily: $…` and badge `NOT AT LOW`.

**Acceptance Scenarios**:

1. **Given** no breach, **When** `render_daily_alert()` runs, **Then** subject omits `— lowest in …` and body shows *not at trailing low* status.
2. **Given** breach `window_key="6m"`, **When** rendered, **Then** subject ends with `— lowest in 6 months`, badge is `LOWEST IN 6 MONTHS`, and headline references that horizon.
3. **Given** `body_html` is set, **When** notifier builds email, **Then** HTML includes window scan table and CID header image reference.

---

### User Story 2 - India pricing display (Priority: P2)

Daily report shows **India retail estimate** and **international parity** when `IndiaGoldQuote` is available; USD-only when INR fetch failed.

**Acceptance Scenarios**:

1. **Given** non-null `india_quote`, **When** HTML renders, **Then** side-by-side retail and parity cards appear plus India 24K reference box with duty/premium breakdown.
2. **Given** `india_quote is None`, **When** body renders, **Then** no India INR lines appear (USD-only report).
3. **Given** `india_quote`, **When** subject is built, **Then** it includes `~₹<retail_per_10g>` after USD close.

---

### User Story 3 - Window scan and last 5 days (Priority: P2)

Report includes full **window scan** (all six horizons) and a **Last 5 trading days** summary row at the bottom of the scan section.

**Acceptance Scenarios**:

1. **Given** `window_evaluations` from `evaluate_windows()`, **When** HTML renders, **Then** table lists all windows with min, date, and status pill.
2. **Given** five recent closes, **When** rendered, **Then** a single summary row appears (not a separate table, not per-window columns).
3. **Given** fallback mode with skipped windows, **When** scan renders, **Then** skipped rows show `Skipped` status.

---

### User Story 4 - System alert templates (Priority: P3)

Hard failure and fallback modes need dedicated Email templates per PRD §5.4–§5.5 with **HTML and plain text**.

**Acceptance Scenarios**:

1. **Given** hard failure with 0 trading days, **When** `render_hard_failure_alert()` runs, **Then** subject is `⛔ GOLD ALERT ENGINE: CRITICAL_DATA_FETCH_ERROR`, body includes retry count, and `body_html` is non-null.
2. **Given** fallback with 180 days, **When** `render_fallback_alert()` runs, **Then** body lists skipped windows (e.g. `1-Year`) and notes daily report follows.
3. **Given** daily report after fallback, **When** `fallback_trading_days=180`, **Then** plain body appends degraded-data note.

---

### Edge Cases

- Timestamp always displayed in IST regardless of input timezone.
- Fallback addendum omitted in full mode (`fallback_trading_days is None`).
- `render_price_alert()` delegates to `render_daily_alert()` (legacy alias for tests).
- Gmail: header image uses CID (`gold-header@gold-price-alert`), not data URIs.

---

## Requirements

### Functional Requirements

- **FR-001**: MUST render unified daily report via `render_daily_alert()` per `prd.md` §5.1.
- **FR-002**: MUST return `AlertMessage` with `subject`, `body`, and `body_html`.
- **FR-003**: MUST accept optional `IndiaGoldQuote`; omit India sections when `None` (`FR-30`).
- **FR-004**: MUST render hard-failure template (`§5.4`) with HTML + plain text.
- **FR-005**: MUST render fallback degraded template (`§5.5`) with HTML + plain text.
- **FR-006**: MUST append fallback addendum to daily plain text when fallback mode was used.
- **FR-007**: MUST include window scan from `list[WindowEvaluation]` and `recent_closes` (last 5 sessions).
- **FR-008**: HTML MUST reference `cid:gold-header@gold-price-alert` for email header image.

### Key Entities

- **`AlertMessage`**: `subject: str`, `body: str`, `body_html: str | None` — consumed by notifier.
- **`IndiaGoldQuote`**: from `pricing.py` — parity + retail estimate fields for display.

---

## Success Criteria

- **SC-001**: Unit tests cover daily report breach vs no-breach subjects, badges, and window scan.
- **SC-002**: Hard failure and fallback templates match PRD structure with HTML bodies.
- **SC-003**: No network I/O in templates module (pure rendering).

## Assumptions

- Notifier attaches CID inline PNG when `body_html` references header CID (`004-notifier-orchestration`).
- `IndiaGoldQuote` is built by `GoldAlertService` on every successful run via `pricing.py`.
- Breach detection short-circuit remains in `analyzer.analyze_lows()` — templates only display breach outcome.
