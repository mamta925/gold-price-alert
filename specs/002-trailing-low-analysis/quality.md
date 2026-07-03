# Quality & Testing Guide: Trailing-Low Analysis & Service Layer

**Feature**: `002-trailing-low-analysis`  
**Modules**: `src/analyzer.py`, `src/service.py`  
**Last updated**: 2026-07-03 (rev 2)

---

## Quick reference

| Command | What it does | Network |
|---|---|---|
| `pytest tests/unit/test_analyzer.py -v` | Analyzer + `evaluate_windows` tests | No |
| `pytest tests/unit/test_service.py -v` | Service tests (mocked) | No |
| `pytest tests/unit/ -v -m "not integration"` | Full unit suite (82 tests) | No |
| `python -c "from src.service import run_daily_analysis; print(run_daily_analysis())"` | Live smoke (fetch + INR) | Yes |

---

## Expected unit test counts

```text
test_analyzer.py   → breach + window scan
test_service.py    → india_quote on every success
Full suite         → 82 passed
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
print('india_quote:', r.india_quote)
print('inr_line:', r.inr_line)
"
```

---

## Test design notes

- **Analyzer**: synthetic `TradingDayClose` lists; no I/O.
- **`analyze_lows()`**: top-down short-circuit for breach only.
- **`evaluate_windows()`**: all six rows for daily report scan (no short-circuit).
- **Service**: inject `fetch_fn` and `inr_fn`; INR fetched on every successful run.
- **Tie behavior**: `current <= window_min` must trigger (PRD).
- **Short-circuit**: when 1y triggers, 10d must not be returned even if mathematically true.

---

## Acceptance mapping

| PRD | Test coverage |
|---|---|
| FR-06 top-down order | `test_windows_ordered_top_down`, `test_new_low_triggers_longest_window_first` |
| FR-07 short-circuit on yes | `test_short_circuit_does_not_return_shorter_window` |
| FR-06/08 no → next window | `test_no_on_all_windows_evaluates_every_eligible_window`, `test_no_on_1y_continues_to_shorter_window` |
| FR-08 no breach → daily report (pipeline) | `test_no_breach_when_today_not_lowest`; main tests in 004 |
| FR-11 previous min | `test_previous_min_excludes_today` |
| FR-28/30 INR on success | `test_inr_fetched_without_breach`, `test_breach_without_inr_still_alerts` |
| Window scan | `test_evaluate_windows_*` |
| Fallback skip | `test_skips_ineligible_long_windows_in_fallback`, `test_fallback_mode_still_computes` |
| Hard failure skip | `test_hard_failure_skips_analysis` |
