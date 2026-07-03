# Contract: Fetcher Module API

**Feature**: `001-gold-price-fetch` | **Module**: `src/fetcher.py`

## Public Functions

### `fetch_gold_closes`

```python
def fetch_gold_closes(
    *,
    ticker: str = "GC=F",
    period: str = "1y",
    max_retries: int = 3,
    retry_delay_seconds: int = 60,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> FetchResult:
    """
    Fetch daily closing prices for Gold Futures from Yahoo Finance.

    Retries on empty or failed responses. Classifies result as full,
    fallback, or hard_failure per spec thresholds.
    """
```

**Preconditions**: Network access to Yahoo Finance (or mocked in tests).

**Postconditions**:
- Returns `FetchResult` with classified `mode`
- Never raises on provider failure — errors encoded in `FetchResult.error_code`
- `closes` ordered oldest → newest

**Side effects**: INFO logs (attempts, mode, count); optional sleep between retries.

---

## Public Types (`src/models.py`)

```python
class FetchMode(str, Enum):
    FULL = "full"
    FALLBACK = "fallback"
    HARD_FAILURE = "hard_failure"

@dataclass(frozen=True)
class TradingDayClose:
    date: date
    close: float

@dataclass(frozen=True)
class FetchResult:
    mode: FetchMode
    trading_days: int
    closes: list[TradingDayClose]
    error_code: str | None = None
    degraded_code: str | None = None
    expected_trading_days: int = 252
```

---

## Internal Functions (testable, not public API)

| Function | Purpose |
|---|---|
| `classify_mode(count: int) -> tuple[FetchMode, str \| None, str \| None]` | Mode + codes from row count |
| `normalize_closes(df: pd.DataFrame) -> list[TradingDayClose]` | DataFrame → validated list |
| `_fetch_history(ticker: str, period: str) -> pd.DataFrame` | Thin yfinance wrapper |

---

## Error Codes

| Constant | When set |
|---|---|
| `CRITICAL_DATA_FETCH_ERROR` | `mode == hard_failure` |
| `DATA_FETCH_DEGRADED` | `mode == fallback` |

---

## Consumer Contract (future analyzer)

The analyzer feature MAY assume:
- `result.closes[-1].close` is `P_current`
- `result.mode` determines which windows are eligible
- Hard failure has empty `closes` — do not analyze
