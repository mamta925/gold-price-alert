# Contract: Service Module API

**Feature**: `002-trailing-low-analysis` | **Module**: `src/service.py`

## Public Class

### `GoldAlertService`

```python
class GoldAlertService:
    def __init__(
        self,
        fetch_fn: Callable[[], FetchResult] = fetch_gold_closes,
        inr_fn: Callable[[], float | None] = fetch_usd_inr_rate,
    ) -> None: ...

    def run(self) -> RunResult: ...
```

**Preconditions**: `fetch_fn` returns valid `FetchResult` per `001` contract.

**Postconditions**:
- Hard failure → `analysis.breach is None`, `india_quote is None`, `should_alert is False`
- Successful fetch → `inr_fn` called; `india_quote` set when rate available
- No breach → `should_alert is False`, `india_quote` may still be set
- Breach → `should_alert is True`, `india_quote` set when rate available

**Side effects**: INFO/WARNING logs; `inr_fn` called on every successful fetch.

---

## Public Functions

### `run_daily_analysis`

```python
def run_daily_analysis() -> RunResult:
    """Convenience wrapper: GoldAlertService().run()"""
```

---

## Types (`src/models.py`)

```python
@dataclass(frozen=True)
class AnalysisResult:
    breach: WindowBreach | None

@dataclass(frozen=True)
class RunResult:
    fetch: FetchResult
    analysis: AnalysisResult
    india_quote: IndiaGoldQuote | None = None

    @property
    def inr_line(self) -> str | None: ...

    @property
    def should_alert(self) -> bool: ...
```

---

## Consumer Contract (notifier / main)

- `main.run_daily_job()` sends daily report on every successful fetch — **not** gated by `should_alert`
- Use `should_alert` / `analysis.breach` for breach highlight copy in templates
- Use `fetch.mode == FALLBACK` for degraded-data email + daily report addendum
- Use `fetch.mode == HARD_FAILURE` for critical failure email (no daily report)
- Pass `RunResult.india_quote` to `render_daily_alert()`
