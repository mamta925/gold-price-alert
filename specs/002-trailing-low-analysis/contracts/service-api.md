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
- Hard failure → `analysis.breach is None`, `inr_line is None`, `should_alert is False`
- No breach → `inr_line is None`, `should_alert is False`
- Breach + INR available → `should_alert is True`, `inr_line` formatted string
- Breach + INR unavailable → `should_alert is True`, `inr_line is None`

**Side effects**: INFO/WARNING logs; `inr_fn` called only when breach exists.

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
    inr_line: str | None = None

    @property
    def should_alert(self) -> bool: ...
```

---

## Consumer Contract (future notifier / main)

- Use `should_alert` to gate price alerts (Email + WhatsApp)
- Use `fetch.mode == FALLBACK` for degraded-data email (notifier responsibility)
- Use `fetch.mode == HARD_FAILURE` for critical failure email
- Pass `RunResult` + breach fields to `templates.py` for message rendering
