# Quickstart: Gold Price Fetch Utility

**Feature**: `001-gold-price-fetch` | **Date**: 2026-07-03

Validate the fetch utility locally before SnapDeploy deployment.

## Prerequisites

- Python 3.11+
- Virtual environment recommended

## Setup

```bash
cd gold-price-alert
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-mock
```

## Run unit tests (primary validation)

```bash
pytest tests/unit/test_fetcher.py -v -m "not integration"
```

**Expected**: All tests pass (mocked yfinance — no network required).

## Manual live fetch (optional integration)

```bash
python -c "
from src.fetcher import fetch_gold_closes
r = fetch_gold_closes()
print(f'mode={r.mode.value} days={r.trading_days} latest={r.closes[-1].close if r.closes else None}')
"
```

**Expected** (healthy market day):
- `mode=full`
- `days` ≥ 252
- `latest` = positive USD price

## Verify mode thresholds (dev REPL)

After implementation, confirm classification:

| Mock count | Expected mode |
|---|---|
| 252 | `full` |
| 180 | `fallback` + `DATA_FETCH_DEGRADED` |
| 5 | `hard_failure` + `CRITICAL_DATA_FETCH_ERROR` |

Use unit tests — do not rely on live API for edge cases.

## Troubleshooting

| Symptom | Check |
|---|---|
| `days` < 252 but mode `full` | Classification bug — count valid rows only |
| Tests take >2 min | Ensure `sleep_fn` mocked in retry tests |
| Import error | Run from repo root; `src/` on PYTHONPATH or install editable |

## Next feature

Once fetch tests pass, proceed to **002-analyzer** (trailing-low detection) consuming `FetchResult`.
