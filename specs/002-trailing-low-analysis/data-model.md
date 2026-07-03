# Data Model: Trailing-Low Analysis & Service Layer

**Feature**: `002-trailing-low-analysis` | **Date**: 2026-07-03

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

**Invariant**: Returned only when `current <= min(full window including today)`.

---

### `AnalysisResult`

| Field | Type | Rules |
|---|---|---|
| `breach` | `WindowBreach \| None` | `None` = no alert condition |

---

### `RunResult`

| Field | Type | Rules |
|---|---|---|
| `fetch` | `FetchResult` | From `001` fetcher |
| `analysis` | `AnalysisResult` | Breach outcome |
| `inr_line` | `str \| None` | Set only when breach exists and INR rate available |

**Computed**:

| Property | Rule |
|---|---|
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

## Analysis Flow

```text
[closes list]
   │
   ▼
len < 10? ──yes──► None
   │
   no
   ▼
For each window top-down:
   N > len? ──yes──► skip
   current <= min(window)? ──no──► next window
   │
   yes
   ▼
Return WindowBreach (STOP)
   │
   (no match after all windows)
   ▼
None
```

## Service Flow

```text
[GoldAlertService.run()]
   │
   ▼
fetch_gold_closes()
   │
   hard_failure? ──yes──► RunResult(breach=None)
   │
   no
   ▼
analyze_lows(closes)
   │
   no breach? ──yes──► RunResult(breach=None)
   │
   breach
   ▼
fetch_usd_inr_rate() → format_inr_per_10g_line (or None)
   │
   ▼
RunResult(should_alert=True)
```
