# Feature Specification: Window-Specific Alert Templates

**Feature Branch**: `003-alert-templates`

**Created**: 2026-07-03

**Status**: Draft

**Input**: Render PRD-compliant Email/WhatsApp message subjects and bodies for price alerts, hard failure, and fallback degraded data.

**PRD traceability**: `prd.md` §5.1–§5.4 (FR-09, FR-11, FR-31), §9 AC-12

**Depends on**: `002-trailing-low-analysis` (`WindowBreach`, `RunResult`), `src/pricing.py`

---

## User Scenarios & Testing

### User Story 1 - Window-specific price alert (Priority: P1)

When a trailing-low breach fires, the notifier needs a **single** subject and body matching the **triggered window's** PRD template (1y through 10d).

**Independent Test**: Given a `WindowBreach` for `6m`, render → subject contains `"6 months"` and body contains formatted USD previous/current.

**Acceptance Scenarios**:

1. **Given** breach `window_key="1y"`, **When** `render_price_alert()` runs, **Then** subject is `🚨 GOLD ALERT: $<current> — Today is the lowest in the last 1 year`.
2. **Given** each of the six window keys, **When** rendered, **Then** subject and body use that window's horizon phrase (not a generic template).
3. **Given** breach fields, **When** body is rendered, **Then** it includes `Previous low: $<prev> → Today: $<current>` using `format_usd`.

---

### User Story 2 - INR parity line handling (Priority: P2)

Alert body must include the pre-formatted INR line from the service when available; omit when `INR=X` failed.

**Acceptance Scenarios**:

1. **Given** non-null `inr_line` from service, **When** body renders, **Then** INR line appears verbatim in body.
2. **Given** `inr_line is None`, **When** body renders, **Then** no `India parity:` line appears (USD-only alert).

---

### User Story 3 - System alert templates (Priority: P3)

Hard failure and fallback modes need dedicated Email templates per PRD §5.3–§5.4.

**Acceptance Scenarios**:

1. **Given** hard failure with 0 trading days, **When** `render_hard_failure_alert()` runs, **Then** subject is `⛔ GOLD ALERT ENGINE: CRITICAL_DATA_FETCH_ERROR` and body includes retry count.
2. **Given** fallback with 180 days, **When** `render_fallback_alert()` runs, **Then** body lists skipped windows (e.g. `1-Year`) and mode `FALLBACK`.
3. **Given** price alert after fallback, **When** `fallback_trading_days=180`, **Then** body appends degraded-data note per §5.4.

---

### Edge Cases

- Timestamp always displayed in IST regardless of input timezone.
- Fallback addendum omitted in full mode (`fallback_trading_days is None`).
- All six windows produce distinct subject horizon phrases.

---

## Requirements

### Functional Requirements

- **FR-001**: MUST render six distinct price-alert templates keyed by `WindowBreach.window_key` (`prd.md` §5.1).
- **FR-002**: Body MUST include horizon headline, previous/current USD, timestamp (IST), and action line.
- **FR-003**: MUST accept optional `inr_line` string; omit INR section when `None` (`FR-30`).
- **FR-004**: MUST render hard-failure template (`§5.3`) with `CRITICAL_DATA_FETCH_ERROR`, count, retries.
- **FR-005**: MUST render fallback degraded template (`§5.4`) with expected/received counts and skipped window list.
- **FR-006**: MUST append fallback addendum to price alert body when fallback mode was used (`§5.4`).

### Key Entities

- **`AlertMessage`**: `subject: str`, `body: str` — consumed by notifier (future).

---

## Success Criteria

- **SC-001**: Unit tests cover all six window subjects + body fields.
- **SC-002**: Hard failure and fallback templates match PRD structure.
- **SC-003**: No network I/O in templates module (pure rendering).

## Assumptions

- Notifier dispatch is out of scope (feature 004).
- `inr_line` is pre-built by `GoldAlertService` via `pricing.py`.
