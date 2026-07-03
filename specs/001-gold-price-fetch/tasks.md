# Tasks: Gold Price Fetch Utility

**Input**: Design documents from `specs/001-gold-price-fetch/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/fetcher-api.md

**Tests**: TDD required (constitution §II, spec assumptions) — write failing tests before implementation.

**Organization**: Tasks grouped by user story for independent delivery.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffold and dependencies

- [x] T001 Create `src/` and `tests/unit/` directory structure per plan.md
- [x] T002 Create empty `src/__init__.py`
- [x] T003 Create `requirements.txt` with pinned `yfinance`, `pandas` per plan.md
- [x] T004 [P] Create `requirements-dev.txt` with pinned `pytest`, `pytest-mock`
- [x] T005 [P] Add `tests/conftest.py` with shared fixtures path and optional `@pytest.mark.integration` marker

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types and constants — blocks all user stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [x] T006 Implement `FetchMode` enum and error constants in `src/models.py` per data-model.md
- [x] T007 Implement `TradingDayClose` and `FetchResult` dataclasses in `src/models.py`
- [x] T008 Implement `classify_mode(count: int)` in `src/fetcher.py` returning mode + error/degraded codes
- [x] T009 [P] Write unit tests for `classify_mode` thresholds (252/251/10/9) in `tests/unit/test_fetcher.py` — run and confirm pass

**Checkpoint**: Mode classification tested; fetch logic can build on this

---

## Phase 3: User Story 1 — Retrieve full year of gold closes (Priority: P1) 🎯 MVP

**Goal**: Fetch GC=F daily closes via yfinance; return ≥252 rows in **full** mode, oldest → newest

**Independent Test**: Mock yfinance returning 252 valid rows → `fetch_gold_closes()` returns `mode=full`, `trading_days>=252`, ordered closes

### Tests for User Story 1 ⚠️ Write FIRST, must FAIL before implementation

- [x] T010 [US1] Add failing test `test_normalize_valid_dataframe` in `tests/unit/test_fetcher.py`
- [x] T011 [US1] Add failing test `test_fetch_full_mode_with_mocked_yfinance` in `tests/unit/test_fetcher.py`
- [x] T012 [US1] Add failing test `test_latest_close_is_last_row` in `tests/unit/test_fetcher.py`

### Implementation for User Story 1

- [x] T013 [US1] Implement `normalize_closes(df)` in `src/fetcher.py` — drop NaN, dedupe dates, validate close > 0
- [x] T014 [US1] Implement `_fetch_history(ticker, period)` wrapping `yfinance.Ticker().history(period="1y")` in `src/fetcher.py`
- [x] T015 [US1] Implement `fetch_gold_closes()` single-attempt path (no retry yet) wiring normalize + classify in `src/fetcher.py`
- [x] T016 [US1] Run `pytest tests/unit/test_fetcher.py -v` — all US1 tests pass

**Checkpoint**: MVP fetch works with mocked data; live fetch optional manually

---

## Phase 4: User Story 2 — Survive transient provider failures (Priority: P2)

**Goal**: Retry 3× with 60s delay; hard failure after exhaustion

**Independent Test**: Mock 2 failures then success → full result; mock 3 failures → `CRITICAL_DATA_FETCH_ERROR`, empty closes

### Tests for User Story 2 ⚠️ Write FIRST, must FAIL before implementation

- [x] T017 [US2] Add failing test `test_retry_succeeds_on_second_attempt` with mocked `sleep_fn` in `tests/unit/test_fetcher.py`
- [x] T018 [US2] Add failing test `test_hard_failure_after_three_failures` in `tests/unit/test_fetcher.py`
- [x] T019 [US2] Add failing test `test_empty_dataframe_triggers_retry` in `tests/unit/test_fetcher.py`

### Implementation for User Story 2

- [x] T020 [US2] Add retry loop with `max_retries=3`, `retry_delay_seconds=60`, injectable `sleep_fn` in `src/fetcher.py`
- [x] T021 [US2] Return `hard_failure` + `CRITICAL_DATA_FETCH_ERROR` when all attempts fail or yield zero valid rows in `src/fetcher.py`
- [x] T022 [US2] Add INFO logging for attempt number and outcome in `src/fetcher.py`
- [x] T023 [US2] Run `pytest tests/unit/test_fetcher.py -v` — all US1 + US2 tests pass

**Checkpoint**: Resilient fetch with retry complete

---

## Phase 5: User Story 3 — Degraded history fallback (Priority: P3)

**Goal**: Classify 10–251 rows as **fallback** with `DATA_FETCH_DEGRADED`; preserve all valid closes

**Independent Test**: Mock 180 rows → `mode=fallback`, `degraded_code=DATA_FETCH_DEGRADED`, `trading_days=180`; mock 5 rows → hard failure

### Tests for User Story 3 ⚠️ Write FIRST, must FAIL before implementation

- [x] T024 [US3] Add failing test `test_fallback_mode_180_days` in `tests/unit/test_fetcher.py`
- [x] T025 [US3] Add failing test `test_hard_failure_below_10_days` in `tests/unit/test_fetcher.py`
- [x] T026 [US3] Add failing test `test_fallback_preserves_all_valid_closes` in `tests/unit/test_fetcher.py`

### Implementation for User Story 3

- [x] T027 [US3] Ensure `fetch_gold_closes()` sets `degraded_code=DATA_FETCH_DEGRADED` and `expected_trading_days=252` on fallback in `src/fetcher.py`
- [x] T028 [US3] Ensure hard failure returns empty `closes` list (not partial) in `src/fetcher.py`
- [x] T029 [US3] Run `pytest tests/unit/test_fetcher.py -v` — all tests pass

**Checkpoint**: All three user stories independently validated

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, optional integration, quickstart validation

- [x] T030 [P] Add optional `@pytest.mark.integration` live fetch test (skipped by default) in `tests/unit/test_fetcher.py`
- [x] T031 [P] Update `specs/001-gold-price-fetch/quickstart.md` if CLI command differs from implementation
- [x] T032 Run full `pytest tests/unit/ -v` and manual live fetch per quickstart.md
- [x] T033 Verify no secrets or credentials referenced in `src/fetcher.py` or tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** → **Phase 2** → **Phase 3 (US1)** → **Phase 4 (US2)** → **Phase 5 (US3)** → **Phase 6**
- US2/US3 extend `fetch_gold_closes()` built in US1 — sequential recommended for single developer

### User Story Dependencies

| Story | Depends on | Independent test |
|---|---|---|
| US1 (P1) | Phase 2 | Mock 252 rows → full mode |
| US2 (P2) | US1 fetch skeleton | Mock retry scenarios |
| US3 (P3) | US1 classify + fetch | Mock 180 / 5 rows |

### Parallel Opportunities

- **Phase 1**: T004, T005 in parallel
- **Phase 2**: T009 after T008 (T009 validates T008)
- **Within each story**: Test tasks T010–T012 (US1) can be written in parallel before implementation

### Parallel Example: User Story 1 Tests

```bash
# Write all US1 tests before implementation (same file, sequential edits OK):
T010 test_normalize_valid_dataframe
T011 test_fetch_full_mode_with_mocked_yfinance
T012 test_latest_close_is_last_row
# Then implement T013 → T015
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1): T010–T016
3. **STOP and VALIDATE**: `pytest tests/unit/test_fetcher.py -v`
4. Optional: manual live fetch

### Full feature delivery

1. Setup + Foundational (T001–T009)
2. US1 → US2 → US3 (T010–T029)
3. Polish (T030–T033)
4. Ready for `/speckit-implement` or next feature (002-analyzer)

---

## Task Summary

| Phase | Tasks | Story |
|---|---|---|
| Setup | T001–T005 (5) | — |
| Foundational | T006–T009 (4) | — |
| US1 P1 | T010–T016 (7) | MVP |
| US2 P2 | T017–T023 (7) | Retry |
| US3 P3 | T024–T029 (6) | Fallback |
| Polish | T030–T033 (4) | — |
| **Total** | **33 tasks** | |

**Suggested MVP scope**: Phase 1 + 2 + 3 (T001–T016) — full-mode fetch with tests

---

## Notes

- Constitution: never commit unless owner asks
- Mock `yfinance` in unit tests — no network in CI
- Mock `time.sleep` via `sleep_fn` in retry tests
- Do not implement analyzer, notifier, or SnapDeploy in this feature
