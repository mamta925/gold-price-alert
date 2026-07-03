# Quality & Testing Guide: Trailing-Low Analysis & Service Layer

**Feature**: `002-trailing-low-analysis`  
**Modules**: `src/analyzer.py`, `src/service.py`  
**Last updated**: 2026-07-03

---

## Quick reference

| Command | What it does | Network |
|---|---|---|
| `pytest tests/unit/test_analyzer.py -v` | 8 analyzer tests | No |
| `pytest tests/unit/test_service.py -v` | 5 service tests (mocked) | No |
| `pytest tests/unit/ -v -m "not integration"` | Full unit suite (36 tests) | No |
| `python -c "from src.service import run_daily_analysis; print(run_daily_analysis())"` | Live smoke (fetch + optional INR) | Yes |

---

## Expected unit test counts

```text
test_analyzer.py   → 8 passed
test_service.py    → 5 passed
Full suite         → 36 passed, 1 deselected (integration)
```

---

## Manual smoke (live data)

```bash
cd gold-price-alert
source .venv/bin/activate
python -c "
from src.service import run_daily_analysis
r = run_daily_analysis()
print('mode:', r.fetch.mode.value)
print('days:', r.fetch.trading_days)
print('should_alert:', r.should_alert)
print('breach:', r.analysis.breach)
print('inr_line:', r.inr_line)
"
```

---

## Test design notes

- **Analyzer**: synthetic `TradingDayClose` lists; no I/O.
- **Service**: inject `fetch_fn` and `inr_fn` to avoid Yahoo calls.
- **Tie behavior**: `current <= window_min` must trigger (PRD).
- **Short-circuit**: when 1y triggers, 10d must not be returned even if mathematically true.

---

## Acceptance mapping

| PRD | Test coverage |
|---|---|
| FR-06 top-down order | `test_windows_ordered_top_down`, `test_new_low_triggers_longest_window_first` |
| FR-07 short-circuit | `test_short_circuit_does_not_return_shorter_window` |
| FR-08 silent no-trigger | `test_no_breach_when_today_not_lowest`, `test_no_breach_returns_without_inr` |
| FR-11 previous min | `test_previous_min_excludes_today` |
| FR-30 INR optional | `test_breach_without_inr_still_alerts` |
| Fallback skip | `test_skips_ineligible_long_windows_in_fallback`, `test_fallback_mode_still_computes` |
| Hard failure skip | `test_hard_failure_skips_analysis` |
