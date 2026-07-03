# Contract: Analyzer Module API

**Feature**: `002-trailing-low-analysis` | **Module**: `src/analyzer.py`

## Public Constants

```python
WINDOWS_TOP_DOWN: tuple[WindowDefinition, ...]
# Order: 1y(252), 6m(126), 3m(63), 1m(21), 15d(15), 10d(10)
```

## Public Functions

### `analyze_lows`

```python
def analyze_lows(closes: list[TradingDayClose]) -> WindowBreach | None:
    """
    Evaluate trailing-low windows top-down. Return the first (longest
    eligible) breach, or None if no window triggers.
    """
```

**Preconditions**:
- `closes` ordered oldest → newest (from `FetchResult`)
- Each `close > 0`

**Postconditions**:
- Returns `None` if `len(closes) < 10`
- Skips windows where `window.n > len(closes)`
- At most one breach; short-circuits on first `current <= window_min`
- `breach.current == closes[-1].close`

**Side effects**: None (pure function)

---

## Types (`src/models.py`)

```python
@dataclass(frozen=True)
class WindowBreach:
    window_key: str
    horizon_label: str
    n: int
    current: float
    previous_min: float
```

---

## Consumer Contract

`GoldAlertService` and future `templates.py` MAY assume:
- `window_key` maps to PRD message keys (`1y`, `6m`, …)
- `previous_min` excludes today's close
- Tie at window minimum still produces a breach
