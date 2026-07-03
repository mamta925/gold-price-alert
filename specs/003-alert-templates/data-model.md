# Data Model: Alert Templates

**Feature**: `003-alert-templates` | **Date**: 2026-07-03 (rev 2)

## Entities

### `AlertMessage`

| Field | Type | Rules |
|---|---|---|
| `subject` | `str` | Email subject / WhatsApp header |
| `body` | `str` | Plain-text body (WhatsApp + email fallback) |
| `body_html` | `str \| None` | HTML email body; `None` only if legacy plain-only path |

---

## Daily Report Subject Patterns

| Condition | Pattern |
|---|---|
| Breach + INR | `🪙 Gold Daily: $<current>, ~₹<retail> — lowest in <horizon>` |
| No breach + INR | `🪙 Gold Daily: $<current>, ~₹<retail>` |
| No breach, no INR | `🪙 Gold Daily: $<current> — Not at trailing low` |

---

## Status Badge Copy

| Condition | Badge text |
|---|---|
| Breach | `LOWEST IN <HORIZON_UPPER>` |
| No breach | `✓ NOT AT LOW` |

---

## Window Scan Table

Built from `list[WindowEvaluation]` (from `analyzer.evaluate_windows`):

| Column | Source |
|---|---|
| Horizon | `horizon_label` |
| Window min | `window_min` / `min_date` |
| Status | `At low` if `is_lowest`, `Above low` if not, `Skipped` if `skipped` |

**Last 5 trading days row**: single summary at table bottom using `recent_closes[-5:]` vs today's close.

---

## Skipped Window Labels (fallback email)

| `window_key` | Label in skipped list |
|---|---|
| `1y` | `1-Year` |
| `6m` | `6-Month` |
| `3m` | `3-Month` |
| `1m` | `1-Month` |
| `15d` | `15-Day` |
| `10d` | `10-Day` |

Skipped when `window.n > trading_days`.

---

## India Display (`IndiaGoldQuote`)

| Field | Display use |
|---|---|
| `retail_per_10g` | Subject suffix, retail card, reference box |
| `parity_per_10g` | Parity card, reference box |
| `import_duty_rate` | 10% — shown in reference breakdown |
| `local_premium_rate` | 4% — shown in reference breakdown |
