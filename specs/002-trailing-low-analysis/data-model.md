# Data Model: Trailing-Low Analysis & Service Layer

**Feature**: `002-trailing-low-analysis` | **Date**: 2026-07-03 (rev 2)

## Enums

Reuses `FetchMode` from `001-gold-price-fetch`.

## Entities

### `WindowBreach`

| Field | Type | Rules |
|---|---|---|
| `window_key` | `str` | One of: `1y`, `6m`, `3m`, `1m`, `15d`, `10d` |
| `horizon_label` | `str` | Human label, e.g. `"1 year"` |
| `n` | `int` | Trading days in window (252, 126, …) |
| `current` | `float` | `P_current` = last close in series |
| `previous_min` | `float` | `min(Window(N) excluding today)` |

**Invariant**: Returned only from `analyze_lows()` when `current <= min(full window including today)`.

---

### `WindowEvaluation`

| Field | Type | Rules |
|---|---|---|
| `window_key` | `str` | Same keys as breach |
| `horizon_label` | `str` | Display label |
| `n` | `int` | Window size |
| `window_min` | `float` | Min close in window (0 if skipped) |
| `min_date` | `date` | Date of window minimum |
| `is_lowest` | `bool` | `current <= window_min` |
| `skipped` | `bool` | `True` when `n > len(closes)` |

Produced by `evaluate_windows()` for daily report scan — **not** used for breach short-circuit.

---

### `AnalysisResult`

| Field | Type | Rules |
|---|---|---|
| `breach` | `WindowBreach \| None` | `None` = no breach condition |

---

### `RunResult`

| Field | Type | Rules |
|---|---|---|
| `fetch` | `FetchResult` | From `001` fetcher |
| `analysis` | `AnalysisResult` | Breach outcome |
| `india_quote` | `IndiaGoldQuote \| None` | Set when INR=X available on successful fetch |

**Computed**:

| Property | Rule |
|---|---|
| `inr_line` | Formatted multi-line summary from `india_quote`; `None` if quote missing |
| `should_alert` | `fetch.mode != HARD_FAILURE` **and** `analysis.breach is not None` |

---

## Window Definitions (constants)

| Order | `window_key` | `horizon_label` | `n` |
|---|---|---|---|
| 1 | `1y` | 1 year | 252 |
| 2 | `6m` | 6 months | 126 |
| 3 | `3m` | 3 months | 63 |
| 4 | `1m` | 1 month | 21 |
| 5 | `15d` | 15 days | 15 |
| 6 | `10d` | 10 days | 10 |

## Analysis Flow (breach detection)

**One-line rules:** no → next window · yes → breach & stop · no on all → no breach (daily report still sent)

```text
[closes list]
   │
   ▼
len < 10? ──yes──► None
   │
   no
   ▼
For each window top-down (252 → … → 10):
   N > len? ──yes──► skip
   current <= min(window)? ──no──► continue
   │
   yes
   ▼
Return WindowBreach (STOP)
   │
   (no match after ALL eligible windows)
   ▼
None → daily report with NOT AT LOW
```

## Window scan flow (display)

```text
evaluate_windows(closes) → list[WindowEvaluation]  # all six rows, no short-circuit
```

## Service Flow

```text
[GoldAlertService.run()]
   │
   ▼
fetch_gold_closes()
   │
   hard_failure? ──yes──► RunResult(breach=None, india_quote=None)
   │
   no
   ▼
analyze_lows(closes) → breach | None
   │
   ▼
fetch_usd_inr_rate() → build_india_gold_quote() (or None)
   │
   ▼
RunResult(india_quote=..., should_alert=breach is not None)
```
