# Quality & Testing Guide: Gold Price Fetch Utility

**Feature**: `001-gold-price-fetch`  
**Module**: `src/fetcher.py` — `fetch_gold_closes()`  
**Last updated**: 2026-07-03

---

## Quick reference

| Command | What it does | Network |
|---|---|---|
| `pytest tests/unit/test_fetcher.py -v -m "not integration"` | **Default** — 18 unit tests, mocked data | No |
| `pytest tests/unit/test_fetcher.py -v -m integration` | Live Yahoo Finance fetch | Yes |
| `pytest tests/unit/test_fetcher.py -v` | All 19 tests | Yes (1 test) |
| Manual `python -c "..."` | Smoke test real GC=F data | Yes |

---

## Setup (one time)

```bash
cd gold-price-alert
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

---

## 1. Unit tests (recommended — no network)

```bash
pytest tests/unit/test_fetcher.py -v -m "not integration"
```

**Expected output:**

```text
18 passed, 1 deselected
```

### Why "1 deselected"?

This is **intentional**, not a failure.

The filter `-m "not integration"` tells pytest to **exclude** tests marked `@pytest.mark.integration`. There is exactly **one** such test:

| Test | File | Why excluded by default |
|---|---|---|
| `test_live_fetch_gc_f` | `tests/unit/test_fetcher.py` | Calls real Yahoo Finance; needs network; may be slow or flaky |

| Count | Meaning |
|---|---|
| **18 passed** | Unit tests using mocked yfinance — fast, offline |
| **1 deselected** | Live integration test skipped by the marker filter |

To run **only** the deselected test:

```bash
pytest tests/unit/test_fetcher.py -v -m integration
```

To run **all 19** tests (no filter):

```bash
pytest tests/unit/test_fetcher.py -v
```

---

## 2. What the 18 unit tests cover

### Mode classification (`classify_mode`)

| Test | Input rows | Expected mode |
|---|---|---|
| `test_full_at_252` | 252 | `full` |
| `test_full_above_252` | 300 | `full` |
| `test_fallback_at_251` | 251 | `fallback` + `DATA_FETCH_DEGRADED` |
| `test_fallback_at_10` | 10 | `fallback` |
| `test_hard_failure_at_9` | 9 | `hard_failure` + `CRITICAL_DATA_FETCH_ERROR` |
| `test_hard_failure_at_zero` | 0 | `hard_failure` |

### Normalization (`normalize_closes`)

- Valid DataFrame → ordered oldest → newest
- Drops NaN, zero, and negative closes
- Dedupes duplicate dates (keeps last)
- Empty DataFrame → empty list

### Fetch orchestration (`fetch_gold_closes`)

| Test | Scenario |
|---|---|
| `test_full_mode_with_mocked_yfinance` | 252 rows → `full` |
| `test_latest_close_is_last_row` | Last row = most recent date |
| `test_retry_succeeds_on_second_attempt` | Empty then success → retry works |
| `test_hard_failure_after_three_failures` | 3 exceptions → `CRITICAL_DATA_FETCH_ERROR` |
| `test_empty_dataframe_triggers_retry` | Empty frames retried until success |
| `test_fallback_mode_180_days` | 180 rows → `fallback` |
| `test_hard_failure_below_10_days` | 5 rows → hard failure, empty `closes` |
| `test_fallback_preserves_all_valid_closes` | Fallback keeps all 180 prices |

---

## 3. Live fetch (manual smoke test)

```bash
python -c "
from src.fetcher import fetch_gold_closes
r = fetch_gold_closes()
print(f'mode={r.mode.value}')
print(f'days={r.trading_days}')
print(f'degraded={r.degraded_code}')
print(f'error={r.error_code}')
if r.closes:
    last = r.closes[-1]
    print(f'latest_date={last.date} close=\${last.close:,.2f}')
"
```

**Expected on a healthy market day:**

```text
mode=full
days=252          # or slightly more
degraded=None
error=None
latest_date=YYYY-MM-DD close=$X,XXX.XX
```

---

## 4. REPL inspection

```bash
python
```

```python
from src.fetcher import fetch_gold_closes

r = fetch_gold_closes()
r.mode          # full | fallback | hard_failure
r.trading_days
r.closes[0]     # oldest trading day
r.closes[-1]    # most recent (P_current candidate)
len(r.closes)
```

---

## 5. Mode reference

| `mode` | Row count | `error_code` | `degraded_code` | `closes` |
|---|---|---|---|---|
| `full` | ≥ 252 | `None` | `None` | All valid rows |
| `fallback` | 10 – 251 | `None` | `DATA_FETCH_DEGRADED` | All valid rows |
| `hard_failure` | < 10 or fetch failed | `CRITICAL_DATA_FETCH_ERROR` | `None` | **Empty list** |

Thresholds align with `prd.md` §3.1 and `data-model.md`.

---

## 6. Integration test

```bash
pytest tests/unit/test_fetcher.py::test_live_fetch_gc_f -v
```

**Asserts:**

- `mode` is `full` or `fallback`
- `trading_days` ≥ 10
- Latest close > 0

Requires internet access to Yahoo Finance.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: src` | Wrong working directory | `cd` to repo root `gold-price-alert/` |
| `18 passed, 1 deselected` | Normal with `-m "not integration"` | Not an error — see §1 above |
| Tests take 2+ minutes | Integration test or unmocked sleep | Use `-m "not integration"` |
| Live fetch `hard_failure` | Yahoo down or no network | Retry; check internet |
| `days` < 252 but `mode=full` | Bug in classification | Should not happen — count valid rows only |

---

## 8. Quality gates (definition of done)

Before marking this feature complete or moving to **002-analyzer**:

- [ ] `pytest tests/unit/test_fetcher.py -v -m "not integration"` → **18 passed**
- [ ] Optional: live smoke test returns `mode=full` and `days` ≥ 252
- [ ] Optional: `pytest -m integration` passes
- [ ] No secrets in `src/fetcher.py` or tests
- [ ] Hard failure returns **empty** `closes` (not partial data)

---

## 9. Related docs

| Doc | Purpose |
|---|---|
| [spec.md](./spec.md) | Requirements |
| [plan.md](./plan.md) | Technical plan |
| [quickstart.md](./quickstart.md) | Short validation steps |
| [contracts/fetcher-api.md](./contracts/fetcher-api.md) | Public API contract |
| [data-model.md](./data-model.md) | Entities and thresholds |
