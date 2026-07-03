# Data Model: Alert Templates

**Feature**: `003-alert-templates` | **Date**: 2026-07-03

## Entities

### `AlertMessage`

| Field | Type | Rules |
|---|---|---|
| `subject` | `str` | Email subject / WhatsApp header |
| `body` | `str` | Plain-text message body |

---

## Window Subject Horizons

| `window_key` | Subject horizon phrase |
|---|---|
| `1y` | `1 year` |
| `6m` | `6 months` |
| `3m` | `3 months` |
| `1m` | `1 month` |
| `15d` | `15 days` |
| `10d` | `10 days` |

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
