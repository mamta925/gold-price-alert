# Tasks: Daily HTML Alert Templates

**Prerequisites**: spec.md, plan.md, data-model.md, contracts/templates-api.md

**Tests**: TDD — write failing tests before `src/templates.py`

**Status**: Complete (2026-07-03, rev 2)

---

## Phase 1: Tests — Daily report (P1)

- [x] T001 [US1] No-breach subject and `NOT AT LOW` badge copy
- [x] T002 [US1] Breach subject suffix `— lowest in <horizon>` and breach headline
- [x] T003 [US1] Plain body includes today's close and window scan lines
- [x] T004 [US1] `body_html` is non-null and contains window scan table

## Phase 2: Tests — India pricing (P2)

- [x] T005 [US2] HTML includes retail + parity cards when `india_quote` set
- [x] T006 [US2] Body omits India block when `india_quote is None`
- [x] T007 [US2] Subject includes `~₹` retail when quote available

## Phase 3: Tests — Window scan & last 5 days (P2)

- [x] T008 [US3] Window scan lists all six horizons with status pills
- [x] T009 [US3] Last 5 days summary row at bottom of scan (single row)
- [x] T010 [US3] Skipped windows show `Skipped` in fallback scenarios

## Phase 4: Tests — System templates (P3)

- [x] T011 [US4] Hard failure subject, body fields, and `body_html`
- [x] T012 [US4] Fallback alert lists skipped windows for 180 days + HTML
- [x] T013 [US4] Fallback addendum appended when `fallback_trading_days` set

## Phase 5: Implementation

- [x] T014 Implement `AlertMessage.body_html`, `render_daily_alert()`, HTML helpers
- [x] T015 Add `src/email_assets.py` + `assets/gold-header.png` CID contract
- [x] T016 HTML for hard failure and fallback system alerts
- [x] T017 Run full unit suite — 82 passed
- [x] T018 Update spec pack and PRD §5

**Checkpoint**: Templates ready for notifier HTML multipart + daily pipeline (004)
