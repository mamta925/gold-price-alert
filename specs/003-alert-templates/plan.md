# Implementation Plan: Window-Specific Alert Templates

**Branch**: `003-alert-templates` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

## Summary

Build `src/templates.py` with pure rendering functions returning `AlertMessage` dataclass. Map six window keys to PRD subject/body formats; include hard-failure and fallback system templates. TDD via `tests/unit/test_templates.py`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `src/pricing.format_usd`, `src/analyzer.WINDOWS_TOP_DOWN`, `src/models` constants

**Testing**: `pytest`; fixed `datetime` fixtures for deterministic output

**Constraints**: IST timestamps (`Asia/Kolkata`); no secrets; no I/O

## Constitution Check

| Gate | Status |
|---|---|
| Spec-driven | ✅ |
| TDD | ✅ |
| Minimal typed Python | ✅ |
| Scope: templates only | ✅ No notifier |

## Source Structure

```text
src/templates.py
tests/unit/test_templates.py
specs/003-alert-templates/
```

## Design

| Function | Purpose |
|---|---|
| `render_price_alert(breach, inr_line, timestamp, fallback_trading_days?)` | §5.1 price alert |
| `render_hard_failure_alert(trading_days, timestamp)` | §5.3 |
| `render_fallback_alert(trading_days, timestamp)` | §5.4 |
| `format_timestamp_ist(dt)` | NFR-06 |
| `skipped_window_labels(trading_days)` | Fallback skipped list |
