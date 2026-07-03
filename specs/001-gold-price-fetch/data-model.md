# Data Model: Gold Price Fetch Utility

**Feature**: `001-gold-price-fetch` | **Date**: 2026-07-03

## Enums

### `FetchMode`

| Value | Condition | `error_code` | `degraded_code` |
|---|---|---|---|
| `full` | `trading_days >= 252` | `None` | `None` |
| `fallback` | `10 <= trading_days <= 251` | `None` | `DATA_FETCH_DEGRADED` |
| `hard_failure` | `trading_days < 10` OR all retries exhausted with no valid data | `CRITICAL_DATA_FETCH_ERROR` | `None` |

## Entities

### `TradingDayClose`

| Field | Type | Rules |
|---|---|---|
| `date` | `date` | Exchange session date (timezone-naive UTC date from yfinance index) |
| `close` | `float` | Must be `> 0` |

**Validation**: Reject NaN, zero, or negative closes during normalization.

---

### `FetchResult`

| Field | Type | Rules |
|---|---|---|
| `mode` | `FetchMode` | Exactly one per run |
| `trading_days` | `int` | `len(closes)` after normalization |
| `closes` | `list[TradingDayClose]` | Ordered oldest → newest; empty on hard_failure |
| `error_code` | `str \| None` | Set only when `mode == hard_failure` |
| `degraded_code` | `str \| None` | Set only when `mode == fallback` |
| `expected_trading_days` | `int` | Always `252` (constant for downstream messages) |

**Invariants**:
- `trading_days == len(closes)` always
- Last close in list = most recent trading session (`P_current` candidate)
- Hard failure → `closes` is empty list (not partial junk)

---

## State Transitions

```text
[Start]
   │
   ▼
[Attempt fetch] ──fail──► retry (max 3) ──all fail──► hard_failure
   │
   success
   │
   ▼
[Normalize rows]
   │
   ▼
[Classify by count]
   ├── >= 252 ──► full
   ├── 10–251 ──► fallback
   └── < 10  ──► hard_failure
```

## Constants

| Name | Value | Source |
|---|---|---|
| `TICKER_DEFAULT` | `GC=F` | prd.md FR-01 |
| `EXPECTED_TRADING_DAYS` | `252` | prd.md D10 |
| `FALLBACK_MIN_DAYS` | `10` | prd.md FR-05a |
| `MAX_RETRIES` | `3` | prd.md NFR-01 |
| `RETRY_DELAY_SECONDS` | `60` | prd.md NFR-01 |
| `HISTORY_PERIOD` | `"1y"` | prd.md FR-02 |
