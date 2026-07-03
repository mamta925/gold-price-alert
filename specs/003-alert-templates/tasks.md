# Tasks: Window-Specific Alert Templates

**Prerequisites**: spec.md, plan.md, data-model.md, contracts/templates-api.md

**Tests**: TDD — write failing tests before `src/templates.py`

**Status**: Complete (2026-07-03)

---

## Phase 1: Tests — Price alerts (P1)

- [x] T001 [US1] Parametrized test: all six windows produce correct subject horizon
- [x] T002 [US1] Body includes previous/current USD and IST timestamp
- [x] T003 [US1] Body includes action line per PRD

## Phase 2: Tests — INR & fallback addendum (P2)

- [x] T004 [US2] Body includes `inr_line` when provided
- [x] T005 [US2] Body omits India parity when `inr_line is None`
- [x] T006 [US3] Fallback addendum appended when `fallback_trading_days` set

## Phase 3: Tests — System templates (P3)

- [x] T007 [US3] Hard failure subject and body fields
- [x] T008 [US3] Fallback alert lists skipped windows for 180 days

## Phase 4: Implementation

- [x] T009 Implement `AlertMessage` and rendering functions in `src/templates.py`
- [x] T010 Run full unit suite — 51 passed
- [x] T011 Add `quality.md` and mark tasks complete

**Checkpoint**: Templates ready for feature 004 (notifier + main orchestration)
