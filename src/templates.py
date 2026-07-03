from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.analyzer import WINDOWS_TOP_DOWN, WindowEvaluation
from src.models import (
    CRITICAL_DATA_FETCH_ERROR,
    EXPECTED_TRADING_DAYS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    TradingDayClose,
    WindowBreach,
)
from src.email_assets import GOLD_HEADER_IMAGE_SRC
from src.pricing import IndiaGoldQuote, format_inr, format_usd

IST = ZoneInfo("Asia/Kolkata")
RECENT_TRADING_DAYS = 5

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
    body_html: str | None = None


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


def _status_headline(breach: WindowBreach | None) -> str:
    if breach is not None:
        return f"Today is the lowest close in the last {breach.horizon_label}"
    return "Today is not at a trailing low"


def _status_detail(breach: WindowBreach | None, current_usd: str) -> str:
    if breach is not None:
        return (
            f"Previous low: {format_usd(breach.previous_min)} → Today: {current_usd}"
        )
    return "Price is above the minimum on every evaluated window."


def _daily_subject(
    latest: TradingDayClose,
    breach: WindowBreach | None,
    india_quote: IndiaGoldQuote | None = None,
) -> str:
    current_usd = format_usd(latest.close)
    if breach is not None:
        return (
            f"🚨 GOLD ALERT: {current_usd} — "
            f"Lowest in the last {breach.horizon_label}"
        )
    if india_quote is not None:
        return (
            f"🪙 Gold Daily: {current_usd}, ~{format_inr(india_quote.retail_per_10g)}"
        )
    return f"🪙 Gold Daily: {current_usd} — Not at trailing low"


def _format_retail_headline_html(quote: IndiaGoldQuote | None) -> str:
    if quote is None:
        return ""
    return f"""
              <p style="margin:20px 0 8px;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af;">
                India retail estimate
              </p>
              <p style="margin:0;font-size:46px;line-height:1.1;font-weight:700;color:#fbbf24;">
                ~ {format_inr(quote.retail_per_10g)}
              </p>"""


def _format_india_quote_html(quote: IndiaGoldQuote | None) -> str:
    if quote is None:
        return ""
    duty_pct = int(quote.import_duty_rate * 100)
    premium_pct = int(quote.local_premium_rate * 100)
    return f"""
              <div style="margin-top:20px;padding:16px 18px;background:#1f1f33;border-radius:12px;border:1px solid #3d3d5c;text-align:left;">
                <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#d4af37;">
                  India 24K Reference
                </p>
                <p style="margin:0 0 6px;font-size:13px;color:#9ca3af;line-height:1.5;">
                  Spot: {format_usd(quote.gold_usd_per_oz)}/oz → {format_usd(quote.usd_per_10g)}/10g
                  @ ₹{quote.usd_inr_rate:.2f}/USD
                </p>
                <p style="margin:0;font-size:15px;color:#e5e7eb;line-height:1.5;">
                  International parity:
                  <strong style="color:#fbbf24;">{format_inr(quote.parity_per_10g)}</strong> / 10g
                  <span style="color:#9ca3af;">({format_inr(quote.parity_per_gram)} / g)</span>
                </p>
                <p style="margin:10px 0 0;font-size:15px;color:#e5e7eb;line-height:1.5;">
                  Approximate India retail:
                  <strong style="color:#fbbf24;">{format_inr(quote.retail_per_10g)}</strong> / 10g
                  <span style="color:#9ca3af;">({format_inr(quote.retail_per_gram)} / g)</span>
                </p>
                <p style="margin:10px 0 0;font-size:11px;color:#9ca3af;line-height:1.5;">
                  Retail headline above includes +{duty_pct}% import duty + {premium_pct}% local premium.
                  Excludes GST &amp; making charges.
                </p>
              </div>"""


def _format_india_quote_text(quote: IndiaGoldQuote | None) -> list[str]:
    if quote is None:
        return []
    from src.pricing import format_india_gold_summary

    return ["", format_india_gold_summary(quote)]


def _last_five_day_check(
    latest: TradingDayClose,
    recent_closes: list[TradingDayClose],
) -> tuple[str, str, str]:
    """Return detail, status label, and color for the last-5-days column."""
    if len(recent_closes) < RECENT_TRADING_DAYS:
        return "Insufficient data", "—", "#9ca3af"

    min_day = min(recent_closes, key=lambda day: day.close)
    detail = f"Low {format_usd(min_day.close)} on {min_day.date}"
    if latest.close <= min_day.close:
        return detail, "Lowest", "#fbbf24"
    return detail, "Above low", "#86efac"


def _window_rows_html(evaluations: list[WindowEvaluation]) -> str:
    rows: list[str] = []
    for evaluation in evaluations:
        if evaluation.skipped:
            status = "Skipped"
            status_color = "#9ca3af"
            detail = "Insufficient history"
        elif evaluation.is_lowest:
            status = "Lowest"
            status_color = "#fbbf24"
            detail = (
                f"{format_usd(evaluation.window_min)} on {evaluation.min_date}"
            )
        else:
            status = "Above low"
            status_color = "#86efac"
            detail = (
                f"Low {format_usd(evaluation.window_min)} on {evaluation.min_date}"
            )

        rows.append(
            "<tr>"
            f'<td style="padding:10px 12px;border-bottom:1px solid #2d2d44;'
            f'color:#e5e7eb;font-size:14px;">{evaluation.horizon_label}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #2d2d44;'
            f'color:#cbd5e1;font-size:13px;">{detail}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #2d2d44;'
            f'color:{status_color};font-size:13px;font-weight:700;text-align:right;">'
            f"{status}</td>"
            "</tr>"
        )
    return "".join(rows)


def _last_five_summary_row_html(
    latest: TradingDayClose,
    recent_closes: list[TradingDayClose],
) -> str:
    detail, status, status_color = _last_five_day_check(latest, recent_closes)
    return (
        "<tr>"
        f'<td style="padding:10px 12px;border-top:1px solid #3d3d5c;background:#1a1a28;'
        f'color:#d4af37;font-size:14px;font-weight:700;">Last 5 days</td>'
        f'<td style="padding:10px 12px;border-top:1px solid #3d3d5c;background:#1a1a28;'
        f'color:#cbd5e1;font-size:13px;">{detail}</td>'
        f'<td style="padding:10px 12px;border-top:1px solid #3d3d5c;background:#1a1a28;'
        f'color:{status_color};font-size:13px;font-weight:700;text-align:right;">'
        f"{status}</td>"
        "</tr>"
    )


def _render_daily_html(
    *,
    latest: TradingDayClose,
    breach: WindowBreach | None,
    evaluations: list[WindowEvaluation],
    india_quote: IndiaGoldQuote | None,
    recent_closes: list[TradingDayClose],
    timestamp: datetime,
    fallback_trading_days: int | None,
) -> str:
    current_usd = format_usd(latest.close)
    headline = _status_headline(breach)
    detail = _status_detail(breach, current_usd)
    ts = format_timestamp_ist(timestamp)

    if breach is not None:
        badge_bg = "#7c2d12"
        badge_border = "#fbbf24"
        badge_text = "🚨 TRAILING LOW"
    else:
        badge_bg = "#14532d"
        badge_border = "#86efac"
        badge_text = "✓ NOT AT LOW"

    fallback_note = ""
    if fallback_trading_days is not None:
        fallback_note = (
            '<p style="margin:16px 0 0;padding:12px;background:#422006;'
            'border-left:4px solid #f59e0b;color:#fde68a;font-size:13px;line-height:1.5;">'
            "⚠️ Fallback data in use "
            f"({fallback_trading_days} trading days, not full 1-year history)."
            "</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gold Daily Report</title>
</head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:Georgia,'Times New Roman',serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0f0f1a;">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0"
               style="max-width:600px;width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:28px 24px;background:linear-gradient(135deg,#3d2b00 0%,#1a1408 55%,#0f0f1a 100%);border-radius:16px 16px 0 0;border:1px solid #5c4a1f;border-bottom:none;text-align:center;">
              <img src="{GOLD_HEADER_IMAGE_SRC}" alt="Gold" width="140"
                   style="display:block;margin:0 auto 16px;border-radius:12px;">
              <p style="margin:0 0 6px;font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#d4af37;">
                GC=F Daily Report
              </p>
              <h1 style="margin:0;font-size:28px;font-weight:700;color:#fff7e6;">
                Gold Price Alert
              </h1>
              <p style="margin:8px 0 0;font-size:14px;color:#c4b58a;">
                {latest.date.strftime("%A, %d %B %Y")}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 24px;background:#171726;border-left:1px solid #2d2d44;border-right:1px solid #2d2d44;text-align:center;">
              <p style="margin:0 0 8px;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af;">
                Today's Close
              </p>
              <p style="margin:0;font-size:46px;line-height:1.1;font-weight:700;color:#fbbf24;">
                {current_usd}
              </p>
              {_format_retail_headline_html(india_quote)}
              <div style="display:inline-block;margin-top:20px;padding:10px 18px;background:{badge_bg};border:1px solid {badge_border};border-radius:999px;color:#fff7ed;font-size:13px;font-weight:700;letter-spacing:0.5px;">
                {badge_text}
              </div>
              <p style="margin:18px 0 0;font-size:16px;color:#e5e7eb;line-height:1.5;">
                {headline}
              </p>
              <p style="margin:8px 0 0;font-size:14px;color:#cbd5e1;line-height:1.5;">
                {detail}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 24px 24px;background:#171726;border-left:1px solid #2d2d44;border-right:1px solid #2d2d44;">
              <p style="margin:0 0 12px;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af;">
                Window Scan
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                     style="border-collapse:collapse;background:#12121f;border-radius:12px;overflow:hidden;border:1px solid #2d2d44;">
                <tr>
                  <th align="left" style="padding:10px 12px;background:#1f1f33;color:#d4af37;font-size:12px;text-transform:uppercase;">Window</th>
                  <th align="left" style="padding:10px 12px;background:#1f1f33;color:#d4af37;font-size:12px;text-transform:uppercase;">Reference Low</th>
                  <th align="right" style="padding:10px 12px;background:#1f1f33;color:#d4af37;font-size:12px;text-transform:uppercase;">Status</th>
                </tr>
                {_window_rows_html(evaluations)}
                {_last_five_summary_row_html(latest, recent_closes)}
              </table>
              {_format_india_quote_html(india_quote)}
              {fallback_note}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 24px;background:#12121f;border:1px solid #2d2d44;border-top:none;border-radius:0 0 16px 16px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
                {ts}<br>
                Source: Yahoo Finance GC=F · India estimates are indicative only.
              </p>
              {"<p style='margin:12px 0 0;font-size:13px;color:#fbbf24;font-weight:700;'>Action: Evaluate current entry positions.</p>" if breach is not None else ""}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _render_daily_text(
    *,
    latest: TradingDayClose,
    breach: WindowBreach | None,
    evaluations: list[WindowEvaluation],
    india_quote: IndiaGoldQuote | None,
    recent_closes: list[TradingDayClose],
    timestamp: datetime,
    fallback_trading_days: int | None,
) -> str:
    lines = [
        "Gold Daily Report (GC=F)",
        "",
        f"Date: {latest.date}",
        f"Today's close: {format_usd(latest.close)}",
    ]
    if india_quote is not None:
        lines.append(
            f"India retail estimate: ~ {format_inr(india_quote.retail_per_10g)} / 10g"
        )
    lines.extend(
        [
            _status_headline(breach),
            _status_detail(breach, format_usd(latest.close)),
        ]
    )
    lines.extend(_format_india_quote_text(india_quote))
    last_five_detail, last_five_status, _ = _last_five_day_check(latest, recent_closes)
    lines.extend(["", "Window scan:"])
    for evaluation in evaluations:
        if evaluation.skipped:
            lines.append(f"  {evaluation.horizon_label}: skipped (insufficient history)")
            continue
        status = "LOWEST" if evaluation.is_lowest else "above low"
        lines.append(
            f"  {evaluation.horizon_label}: {format_usd(evaluation.window_min)} "
            f"on {evaluation.min_date} — {status}"
        )
    lines.append(
        f"  Last 5 days: {last_five_detail} — {last_five_status.lower()}"
    )
    lines.extend(["", f"Timestamp: {format_timestamp_ist(timestamp)}"])
    if breach is not None:
        lines.append("Action: Evaluate current entry positions.")
    if fallback_trading_days is not None:
        lines.extend(
            [
                "",
                "⚠️ Note: This report used fallback data "
                f"({fallback_trading_days} trading days available, "
                "not full 252-day / 1-year history).",
            ]
        )
    return "\n".join(lines)


def render_daily_alert(
    *,
    latest: TradingDayClose,
    breach: WindowBreach | None,
    window_evaluations: list[WindowEvaluation],
    india_quote: IndiaGoldQuote | None,
    recent_closes: list[TradingDayClose],
    timestamp: datetime,
    fallback_trading_days: int | None = None,
) -> AlertMessage:
    subject = _daily_subject(latest, breach, india_quote)
    body = _render_daily_text(
        latest=latest,
        breach=breach,
        evaluations=window_evaluations,
        india_quote=india_quote,
        recent_closes=recent_closes,
        timestamp=timestamp,
        fallback_trading_days=fallback_trading_days,
    )
    body_html = _render_daily_html(
        latest=latest,
        breach=breach,
        evaluations=window_evaluations,
        india_quote=india_quote,
        recent_closes=recent_closes,
        timestamp=timestamp,
        fallback_trading_days=fallback_trading_days,
    )
    return AlertMessage(subject=subject, body=body, body_html=body_html)


def render_price_alert(
    breach: WindowBreach,
    *,
    india_quote: IndiaGoldQuote | None,
    timestamp: datetime,
    fallback_trading_days: int | None = None,
    window_closes: list[TradingDayClose] | None = None,
) -> AlertMessage:
    latest = (
        window_closes[-1]
        if window_closes
        else TradingDayClose(date=timestamp.date(), close=breach.current)
    )
    from src.analyzer import evaluate_windows

    return render_daily_alert(
        latest=latest,
        breach=breach,
        window_evaluations=evaluate_windows(window_closes or [latest]),
        india_quote=india_quote,
        recent_closes=(window_closes or [latest])[-RECENT_TRADING_DAYS:],
        timestamp=timestamp,
        fallback_trading_days=fallback_trading_days,
    )


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
            "The daily gold report follows with today's price and window scan.",
        ]
    )
    return AlertMessage(subject=subject, body=body)
