# Implementation Plan: Gold Price Fetch Utility

**Branch**: `001-gold-price-fetch` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-gold-price-fetch/spec.md`

## Summary

Build a typed Python fetch utility (`src/fetcher.py`) that pulls ~1 year of `GC=F` daily closes via `yfinance`, normalizes rows into `TradingDayClose` records, classifies the run as **full** / **fallback** / **hard_failure**, and retries transient failures 3× with 60s delay. Returns a `FetchResult` dataclass for downstream analyzer (future feature). TDD: unit tests with mocked yfinance responses first.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `yfinance` (market data), `pandas` (DataFrame normalization only in fetcher)

**Storage**: N/A — in-memory only; no database

**Testing**: `pytest` + `pytest-mock` (mock `yfinance.Ticker.history`)

**Target Platform**: SnapDeploy Linux container (local dev on macOS)

**Project Type**: Single Python library module within headless alert engine

**Performance Goals**: Complete fetch + retries within 5 minutes (spec SC-005)

**Constraints**: 512 MB RAM; no secrets in fetch path; pin deps in `requirements.txt`

**Scale/Scope**: 1 ticker, 1 fetch per daily run, ~252 rows max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| Spec-driven / PRD-grounded | ✅ Pass | Aligns with `prd.md` §3.1, D10 |
| TDD non-negotiable | ✅ Pass | Tests before `fetcher.py` implementation |
| Minimal typed Python | ✅ Pass | Dataclasses + type hints; no extra abstractions |
| Scope discipline | ✅ Pass | Fetch only; no alerts/analyzer/HTTP |
| No secret logging | ✅ Pass | Fetch has no credentials |
| yfinance for GC=F | ✅ Pass | Per constitution engineering constraints |

**Post-design re-check**: ✅ No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-gold-price-fetch/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── fetcher-api.md   # Public module contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks (next step)
```

### Source Code (this feature)

```text
gold-price-alert/
├── requirements.txt
├── requirements-dev.txt   # pytest, pytest-mock (optional split)
├── src/
│   ├── __init__.py
│   ├── models.py          # FetchMode, TradingDayClose, FetchResult
│   └── fetcher.py         # fetch_gold_closes(), retry + classify
└── tests/
    └── unit/
        └── test_fetcher.py
```

**Structure Decision**: Single-project layout matching `prd.md` §7. Split `models.py` from `fetcher.py` so tests can validate mode classification without mocking network.

## Phase 0: Research Summary

See [research.md](./research.md). All technical choices resolved — no NEEDS CLARIFICATION remain.

## Phase 1: Design Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Data model | [data-model.md](./data-model.md) | Entities, enums, validation rules |
| API contract | [contracts/fetcher-api.md](./contracts/fetcher-api.md) | Public function signatures |
| Quickstart | [quickstart.md](./quickstart.md) | Local validation steps |

## Implementation Approach

### Module boundaries

```
fetch_gold_closes()  →  _fetch_raw()  →  yfinance Ticker("GC=F").history(period="1y")
                     →  _normalize()  →  list[TradingDayClose]
                     →  _classify()   →  FetchMode + error/degraded codes
                     →  _with_retry() →  wraps _fetch_raw with 3× / 60s
```

### Mode classification (single source of truth)

```python
FULL_THRESHOLD = 252
FALLBACK_MIN = 10

if count >= FULL_THRESHOLD: mode = FULL
elif count >= FALLBACK_MIN: mode = FALLBACK, degraded_code = DATA_FETCH_DEGRADED
else: mode = HARD_FAILURE, error_code = CRITICAL_DATA_FETCH_ERROR
```

### Test strategy (TDD order)

1. `test_classify_mode_full_fallback_hard` — pure function, no mocks
2. `test_normalize_drops_invalid_and_dedupes_dates`
3. `test_retry_succeeds_on_second_attempt` — mock `_fetch_raw`
4. `test_hard_failure_after_three_empty_responses`
5. `test_integration_live_fetch` — optional, `@pytest.mark.integration`, skipped in CI

### Dependencies to pin (initial)

```
yfinance>=0.2.40,<1
pandas>=2.0,<3
pytest>=8.0
pytest-mock>=3.12
```

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| yfinance API change | Pin version; integration test; fallback mode still works on partial data |
| Retry tests slow (60s sleeps) | Inject `sleep_fn` parameter or mock `time.sleep` in tests |
| `history(period="1y")` returns <252 on holidays | Accept as fallback if 10–251; matches PRD |

## Complexity Tracking

> Not applicable — no constitution violations.
