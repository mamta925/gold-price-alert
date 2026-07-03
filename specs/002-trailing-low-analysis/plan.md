# Implementation Plan: Trailing-Low Analysis & Service Layer

**Branch**: `002-trailing-low-analysis` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-trailing-low-analysis/spec.md`

## Summary

Build `src/analyzer.py` for top-down trailing-low detection and `src/service.py` (`GoldAlertService`) to orchestrate fetch → analyze → optional INR parity line. Extend `src/models.py` with `WindowBreach`, `AnalysisResult`, and `RunResult`. TDD with mocked fetch and INR dependencies.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `src/fetcher.py`, `src/pricing.py` (existing)

**Storage**: N/A — in-memory only

**Testing**: `pytest` + `pytest-mock`; inject `fetch_fn` and `inr_fn` on service

**Target Platform**: SnapDeploy Linux container

**Project Type**: Library modules within headless alert engine

**Performance Goals**: Analysis <10ms on 252 rows

**Constraints**: Window math in USD only; INR at notification-prep time only

**Scale/Scope**: 6 windows, 1 breach max per run

## Constitution Check

| Gate | Status | Notes |
|---|---|---|
| Spec-driven / PRD-grounded | ✅ Pass | FR-06–FR-12, FR-27–FR-30 |
| TDD non-negotiable | ✅ Pass | Tests in `test_analyzer.py`, `test_service.py` |
| Minimal typed Python | ✅ Pass | Pure functions + thin service class |
| Scope discipline | ✅ Pass | No notifier/templates/HTTP |
| Market logic integrity | ✅ Pass | Trading-day N values, top-down short-circuit |
| No secret logging | ✅ Pass | No credentials in analyzer/service |

**Post-design re-check**: ✅ No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-trailing-low-analysis/
├── spec.md
├── plan.md              # This file
├── data-model.md
├── contracts/
│   ├── analyzer-api.md
│   └── service-api.md
├── tasks.md
└── quality.md
```

### Source (this feature)

```text
src/
├── models.py      # + WindowBreach, AnalysisResult, RunResult
├── analyzer.py    # analyze_lows(), WINDOWS_TOP_DOWN
└── service.py     # GoldAlertService, run_daily_analysis()

tests/unit/
├── test_analyzer.py
└── test_service.py
```

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Window config | Frozen `WindowDefinition` tuple | Matches PRD table; no runtime config in v1 |
| Short-circuit | Return on first `<=` match | PRD FR-07 / FR-10 |
| Service DI | `fetch_fn`, `inr_fn` callables | Testability without network |
| INR timing | Only on breach | Avoid unnecessary `INR=X` calls (FR-30 behavior) |

## Out of Scope (this feature)

- Email/WhatsApp dispatch (`notifier.py`)
- Alert templates (`templates.py`)
- Fallback degraded **notification** (email before analysis — wired in main/notifier)
- HTTP `/run` endpoint
