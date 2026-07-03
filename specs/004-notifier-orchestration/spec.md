# Feature Specification: Notifier & Daily Pipeline Orchestration

**Feature Branch**: `004-notifier-orchestration`

**Created**: 2026-07-03

**Status**: Draft

**Input**: Email (SMTP) + WhatsApp (Twilio) dispatch, env config, and `main.py` daily pipeline wiring fetch → notify.

**PRD traceability**: §3.3 (FR-13–FR-18), §8 env vars, §9 AC-04–AC-09, AC-11

**Depends on**: `001` fetcher, `002` service/analyzer, `003` templates

---

## User Scenarios & Testing

### User Story 1 - Send price alert on both channels (Priority: P1)

When a trailing-low breach fires, user receives Email + WhatsApp with the rendered template.

**Acceptance Scenarios**:

1. **Given** `should_alert=True`, **When** pipeline runs, **Then** Email and WhatsApp are both dispatched.
2. **Given** no breach, **When** pipeline runs, **Then** no notifications sent (silent exit).

---

### User Story 2 - System alerts email-only (Priority: P2)

Hard failure and fallback degraded alerts go Email only (no WhatsApp).

**Acceptance Scenarios**:

1. **Given** hard failure fetch, **When** pipeline runs, **Then** hard-failure Email sent; WhatsApp not called.
2. **Given** fallback mode, **When** pipeline runs, **Then** degraded Email sent **before** price alert evaluation; if breach follows, price alert uses Email + WhatsApp.

---

### User Story 3 - Config from environment (Priority: P3)

All credentials and recipients load from env vars; missing required vars fail fast.

**Acceptance Scenarios**:

1. **Given** required env vars set, **When** `load_config()` runs, **Then** returns typed `AppConfig`.
2. **Given** missing `SMTP_USER`, **When** `load_config()` runs, **Then** raises `ConfigError`.

---

## Requirements

- **FR-001**: SMTP email via SSL (`smtp.gmail.com:465` defaults).
- **FR-002**: WhatsApp via Twilio REST API — price alerts only.
- **FR-003**: Injectable send functions for unit tests (no real network).
- **FR-004**: `main.run_daily_job()` orchestrates: fetch → hard fail / fallback email → analyze → price alert.
- **FR-005**: `.env.example` documents all required variables (no secrets in git).

---

## Out of Scope

- `app.py` HTTP `/run` endpoint (feature 005)
- GitHub Actions workflow (feature 005)

## Success Criteria

- **SC-001**: Unit tests for config, notifier, main — all pass without network.
- **SC-002**: Notification routing matches constitution §VI table.
