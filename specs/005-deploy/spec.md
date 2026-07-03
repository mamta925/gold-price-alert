# Feature Specification: SnapDeploy HTTP Deploy & GitHub Actions Schedule

**Feature Branch**: `005-deploy`

**Created**: 2026-07-03

**Status**: Draft

**PRD traceability**: §3.1.2 (FR-19–FR-26), §9 AC-10, AC-10a, AC-11

**Depends on**: `004-notifier-orchestration` (`main.run_daily_job`)

---

## User Scenarios

### User Story 1 - Protected daily trigger (Priority: P1)

GitHub Actions wakes SnapDeploy at 08:30 IST via authenticated `POST /run`.

**Acceptance Scenarios**:

1. **Given** valid `X-Cron-Secret` header, **When** `POST /run`, **Then** pipeline runs and returns JSON status.
2. **Given** missing or wrong secret, **When** `POST /run`, **Then** returns **401** without running job.
3. **Given** `CRON_SECRET` unset on server, **When** `POST /run`, **Then** returns **503** (misconfigured).

---

### User Story 2 - Health check (Priority: P2)

SnapDeploy and operators can probe liveness via `GET /health`.

**Acceptance Scenarios**:

1. **Given** app running, **When** `GET /health`, **Then** returns **200** JSON `{status: ok}`.

---

### User Story 3 - Scheduled cron (Priority: P3)

GitHub Actions fires once daily at **08:30 IST** (03:00 UTC).

**Acceptance Scenarios**:

1. **Given** repo secrets `SNAPDEPLOY_APP_URL` and `CRON_SECRET`, **When** workflow runs, **Then** sends authenticated POST to `/run`.

---

## Requirements

- **FR-001**: `app.py` exposes Flask app on `PORT` (default 8000).
- **FR-002**: Auth via `X-Cron-Secret` header or `?secret=` query param.
- **FR-003**: `/run` response JSON includes job `status`, fetch mode, optional `window_key`.
- **FR-004**: `.github/workflows/daily-alert.yml` cron `0 3 * * *` + `workflow_dispatch`.
- **FR-005**: No secrets in git; workflow uses GitHub secrets only.

## Out of Scope

- SnapDeploy dashboard setup (manual)
- Dockerfile (SnapDeploy auto-build)

## Success Criteria

- **SC-001**: HTTP unit tests pass without network.
- **SC-002**: Full unit suite remains green.
