from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.analyzer import WINDOWS_TOP_DOWN
from src.models import (
    CRITICAL_DATA_FETCH_ERROR,
    EXPECTED_TRADING_DAYS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    WindowBreach,
)
from src.pricing import format_usd

IST = ZoneInfo("Asia/Kolkata")

WINDOW_SKIP_LABELS: dict[str, str] = {
    "1y": "1-Year",
    "6m": "6-Month",
    "3m": "3-Month",
    "1m": "1-Month",
    "15d": "15-Day",
    "10d": "10-Day",
}


@dataclass(frozen=True)
class AlertMessage:
    subject: str
    body: str


def format_timestamp_ist(dt: datetime) -> str:
    if dt.tzinfo is None:
        localized = dt.replace(tzinfo=IST)
    else:
        localized = dt.astimezone(IST)
    return localized.strftime("%Y-%m-%d %H:%M:%S IST")


def skipped_window_labels(trading_days: int) -> list[str]:
    return [
        WINDOW_SKIP_LABELS[window.key]
        for window in WINDOWS_TOP_DOWN
        if window.n > trading_days
    ]


def render_price_alert(
    breach: WindowBreach,
    *,
    inr_line: str | None,
    timestamp: datetime,
    fallback_trading_days: int | None = None,
) -> AlertMessage:
    current_usd = format_usd(breach.current)
    subject = (
        f"🚨 GOLD ALERT: {current_usd} — "
        f"Today is the lowest in the last {breach.horizon_label}"
    )

    body_lines = [
        "Gold trailing-low alert (GC=F)",
        "",
        f"📉 Today is the lowest Gold close (GC=F) in the last **{breach.horizon_label}**.",
        f"Previous low: {format_usd(breach.previous_min)} → Today: {current_usd}",
    ]
    if inr_line is not None:
        body_lines.append(inr_line)
    body_lines.extend(
        [
            "",
            f"Timestamp: {format_timestamp_ist(timestamp)}",
            "Action: Evaluate current entry positions.",
        ]
    )
    if fallback_trading_days is not None:
        body_lines.extend(
            [
                "",
                "⚠️ Note: This alert used fallback data "
                f"({fallback_trading_days} trading days available, "
                "not full 252-day / 1-year history).",
            ]
        )

    return AlertMessage(subject=subject, body="\n".join(body_lines))


def render_hard_failure_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    subject = f"⛔ GOLD ALERT ENGINE: {CRITICAL_DATA_FETCH_ERROR}"
    body = "\n".join(
        [
            "The Gold price alert engine could not fetch usable market data for GC=F.",
            "",
            f"Error: {CRITICAL_DATA_FETCH_ERROR}",
            f"Trading days received: {trading_days}",
            f"Retries exhausted: {MAX_RETRIES} attempts with {RETRY_DELAY_SECONDS}s delay",
            f"Timestamp: {format_timestamp_ist(timestamp)}",
            "",
            "No low-detection was performed. Investigate Yahoo Finance connectivity or ticker availability.",
        ]
    )
    return AlertMessage(subject=subject, body=body)


def render_fallback_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    skipped = skipped_window_labels(trading_days)
    skipped_text = ", ".join(skipped) if skipped else "none"
    subject = f"⚠️ GOLD ALERT ENGINE: Running on Fallback Data ({trading_days} days)"
    body = "\n".join(
        [
            "Yahoo Finance returned incomplete history for GC=F.",
            "",
            f"Expected: {EXPECTED_TRADING_DAYS} trading days (~1 calendar year)",
            f"Received: {trading_days} trading days",
            "Mode: FALLBACK — using available recent days only",
            f"Skipped windows: {skipped_text}",
            f"Timestamp: {format_timestamp_ist(timestamp)}",
            "",
            "Low-detection will proceed top-down for eligible windows (first match wins). "
            "A separate price alert follows if a window triggers.",
        ]
    )
    return AlertMessage(subject=subject, body=body)
