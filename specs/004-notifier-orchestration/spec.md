# Feature Specification: Notifier & Daily Pipeline Orchestration

**Feature Branch**: `004-notifier-orchestration`

**Created**: 2026-07-03

**Status**: Implemented (rev 2 — daily reports + HTML email)

**Input**: Email (SMTP multipart HTML) + WhatsApp (Twilio) dispatch, env config, and `main.py` daily pipeline wiring fetch → notify.

**PRD traceability**: §3.3 (FR-13–FR-18), §5.1, §8 env vars, §9 AC-04–AC-06, AC-14–AC-16

**Depends on**: `001` fetcher, `002` service/analyzer, `003` templates, `src/email_assets.py`

---

## User Scenarios & Testing

### User Story 1 - Send daily report on both channels (Priority: P1)

When fetch succeeds (full or fallback), user receives Email (HTML + plain) and WhatsApp (plain text) with the daily gold report.

**Acceptance Scenarios**:

1. **Given** successful fetch with or without breach, **When** pipeline runs, **Then** Email and WhatsApp are both dispatched.
2. **Given** no breach, **When** pipeline runs, **Then** daily report still sent (status `daily_report` or `fallback_daily`).
3. **Given** breach, **When** pipeline runs, **Then** status is `price_alert` or `fallback_price_alert`.

---

### User Story 2 - System alerts email-only (Priority: P2)

Hard failure and fallback degraded alerts go Email only (no WhatsApp). Daily report follows fallback notice in same run.

**Acceptance Scenarios**:

1. **Given** hard failure fetch, **When** pipeline runs, **Then** hard-failure Email sent; WhatsApp not called; no daily report.
2. **Given** fallback mode, **When** pipeline runs, **Then** degraded Email sent **before** daily report; daily report uses Email + WhatsApp.

---

### User Story 3 - HTML email with inline header image (Priority: P2)

Daily and system emails with `body_html` are sent as multipart messages; gold header PNG attached via CID when referenced.

**Acceptance Scenarios**:

1. **Given** daily alert with `body_html` containing `cid:gold-header@gold-price-alert`, **When** `build_email_message()` runs, **Then** message is `multipart/related` with inline PNG.
2. **Given** missing `assets/gold-header.png`, **When** building email, **Then** warning logged; HTML still sent without attachment.

---

### User Story 4 - Config from environment (Priority: P3)

All credentials and recipients load from env vars; missing required vars fail fast.

**Acceptance Scenarios**:

1. **Given** required env vars set, **When** `load_config()` runs, **Then** returns typed `AppConfig`.
2. **Given** missing `SMTP_USER`, **When** `load_config()` runs, **Then** raises `ConfigError`.

---

## Requirements

- **FR-001**: SMTP email via SSL (`smtp.gmail.com:465` defaults); HTML via `add_alternative` or `multipart/related`.
- **FR-002**: WhatsApp via Twilio REST API — **daily gold report only** (plain `body`).
- **FR-003**: Injectable send functions for unit tests (no real network).
- **FR-004**: `main.run_daily_job()` orchestrates: fetch → hard fail email / fallback email → analyze + INR → `render_daily_alert()` → notify.
- **FR-005**: `.env.example` documents all required variables (no secrets in git).
- **FR-006**: `build_email_message()` attaches CID inline image when HTML references `GOLD_HEADER_CID` and file exists.

---

## Out of Scope

- `app.py` HTTP `/run` endpoint (feature 005)
- GitHub Actions workflow (feature 005)

## Success Criteria

- **SC-001**: Unit tests for config, notifier (including CID build), main — all pass without network.
- **SC-002**: Notification routing matches constitution §VI table (rev 2).
