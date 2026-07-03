# Tasks: Trailing-Low Analysis & Service Layer

**Input**: Design documents from `specs/002-trailing-low-analysis/`

**Prerequisites**: `001-gold-price-fetch` complete; `src/pricing.py` available

**Tests**: TDD required — write failing tests before implementation.

**Status**: All tasks complete (2026-07-03)

---

## Phase 1: Foundational Models

- [x] T001 Add `WindowBreach`, `AnalysisResult`, `RunResult` to `src/models.py` per data-model.md
- [x] T002 Add `should_alert` property on `RunResult`

---

## Phase 2: User Story 1 — Trailing-low detection (P1)

### Tests FIRST

- [x] T003 [US1] `test_new_low_triggers_longest_window_first`
- [x] T004 [US1] `test_short_circuit_does_not_return_shorter_window`
- [x] T005 [US1] `test_no_breach_when_today_not_lowest`
- [x] T006 [US1] `test_tie_at_window_low_triggers`
- [x] T007 [US1] `test_previous_min_excludes_today`
- [x] T008 [US1] `test_insufficient_data_returns_none`
- [x] T009 [US1] `test_windows_ordered_top_down`

### Implementation

- [x] T010 [US1] Implement `WINDOWS_TOP_DOWN` and `analyze_lows()` in `src/analyzer.py`

---

## Phase 3: User Story 2 — Fallback eligibility (P2)

### Tests FIRST

- [x] T011 [US2] `test_skips_ineligible_long_windows_in_fallback`

### Implementation

- [x] T012 [US2] Skip logic `if window.n > len(closes): continue` in analyzer

---

## Phase 4: User Story 3 — Service orchestration (P3)

### Tests FIRST

- [x] T013 [US3] `test_hard_failure_skips_analysis`
- [x] T014 [US3] `test_no_breach_returns_without_inr`
- [x] T015 [US3] `test_breach_includes_inr_line_when_rate_available`
- [x] T016 [US3] `test_breach_without_inr_still_alerts`
- [x] T017 [US3] `test_fallback_mode_still_computes`

### Implementation

- [x] T018 [US3] Implement `GoldAlertService` and `run_daily_analysis()` in `src/service.py`
- [x] T019 [US3] Document public API in `contracts/analyzer-api.md` and `contracts/service-api.md`

---

## Phase 5: Quality gate

- [x] T020 Run `pytest tests/unit/ -m "not integration"` — 36 passed
- [x] T021 Add `quality.md` testing guide

**Checkpoint**: Analyzer + service ready for feature 003 (templates + notifier)
