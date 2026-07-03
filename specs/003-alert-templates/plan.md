# Implementation Plan: Daily HTML Alert Templates

**Branch**: `003-alert-templates` | **Date**: 2026-07-03 (rev 2) | **Spec**: [spec.md](./spec.md)

## Summary

Build `src/templates.py` with `render_daily_alert()` returning `AlertMessage` (subject, plain body, HTML body). Unified daily report replaces six separate window templates; breach status changes copy within one template. System alerts (hard failure, fallback) share HTML email shell. TDD via `tests/unit/test_templates.py`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `src/pricing` (`IndiaGoldQuote`, `format_usd`, `format_inr`), `src/analyzer` (`WindowEvaluation`), `src/models`, `src/email_assets` (CID constant referenced in HTML only)

**Testing**: `pytest`; fixed `datetime` fixtures for deterministic output

**Constraints**: IST timestamps (`Asia/Kolkata`); no secrets; no I/O in templates module

## Constitution Check

| Gate | Status |
|---|---|
| Spec-driven | ✅ PRD §5.1 updated |
| TDD | ✅ |
| Minimal typed Python | ✅ |
| Scope: templates only | ✅ Notifier CID attach in 004 |

## Source Structure

```text
src/templates.py
src/email_assets.py          # CID path constants (used by notifier)
assets/gold-header.png       # Committed asset for deploy
tests/unit/test_templates.py
specs/003-alert-templates/
```

## Design

| Function | Purpose |
|---|---|
| `render_daily_alert(...)` | §5.1 unified daily report (HTML + text) |
| `render_price_alert(...)` | Delegates to daily alert (test/back-compat) |
| `render_hard_failure_alert(...)` | §5.4 HTML + plain |
| `render_fallback_alert(...)` | §5.5 HTML + plain |
| `format_timestamp_ist(dt)` | NFR-06 |
| `skipped_window_labels(trading_days)` | Fallback skipped list |
| `_wrap_email_document`, `_email_header`, … | Shared HTML shell |

## HTML Design Tokens

Dark background (`#080810`), gold accents, responsive table layout, status pills for window scan. Header image via CID (not emoji or data URI) for Gmail compatibility.
