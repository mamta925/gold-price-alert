# Research: Gold Price Fetch Utility

**Feature**: `001-gold-price-fetch` | **Date**: 2026-07-03

## R1: Market data library

**Decision**: Use `yfinance` with `Ticker("GC=F").history(period="1y")`.

**Rationale**:
- Specified in `prd.md` and constitution engineering constraints.
- No API key required for v1.
- `period="1y"` returns ~252 daily rows for US futures — matches 1-year trading-day window (D10).

**Alternatives considered**:
- Direct Yahoo Finance HTTP — more brittle; yfinance handles parsing.
- Alpha Vantage / paid APIs — out of scope; adds API key management.

---

## R2: Data normalization

**Decision**: Convert yfinance DataFrame to `list[TradingDayClose]` using `Close` column; drop NaN closes; dedupe by date (keep last).

**Rationale**:
- Spec edge cases: invalid rows excluded, duplicate dates resolved.
- pandas already a project dependency for downstream analyzer.

**Alternatives considered**:
- Raw list of tuples — loses type safety per constitution §III.

---

## R3: Retry implementation

**Decision**: Loop 3 attempts; on empty DataFrame or raised exception, sleep 60s and retry; inject optional `sleep: Callable[[float], None] = time.sleep` for fast tests.

**Rationale**:
- Matches `prd.md` NFR-01 exactly.
- Injectable sleep avoids 120s+ test runtime.

**Alternatives considered**:
- `tenacity` library — rejected; unnecessary dependency for fixed 3× policy.

---

## R4: Public API shape

**Decision**: Single entry point `fetch_gold_closes(*, ticker: str = "GC=F", ...) -> FetchResult`.

**Rationale**:
- Spec SC-006: independently invocable.
- Default ticker matches PRD; parameter allows test overrides without env vars.

**Alternatives considered**:
- Class-based fetcher — rejected; constitution prefers plain functions.

---

## R5: Error code constants

**Decision**: String constants in `models.py`:

```python
CRITICAL_DATA_FETCH_ERROR = "CRITICAL_DATA_FETCH_ERROR"
DATA_FETCH_DEGRADED = "DATA_FETCH_DEGRADED"
EXPECTED_TRADING_DAYS = 252
```

**Rationale**: Downstream notifier (future feature) matches on exact strings from `prd.md`.

---

## R6: Logging

**Decision**: Use `logging` module at INFO for attempt count, mode, trading_days; no price dumps at DEBUG in production path.

**Rationale**: Constitution §V — structured logs without excessive data leakage.
