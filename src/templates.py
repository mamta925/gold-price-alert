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

# Email design tokens (inline styles for client compatibility)
_C_BG = "#080810"
_C_PANEL = "#12121f"
_C_CARD = "#171726"
_C_BORDER = "#2d2d44"
_C_GOLD = "#d4af37"
_C_GOLD_BRIGHT = "#fbbf24"
_C_TEXT = "#e5e7eb"
_C_MUTED = "#9ca3af"
_C_FONT = "Georgia,'Times New Roman',serif"
_C_FONT_UI = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif"


def _status_pill(label: str, color: str, bg: str) -> str:
    return (
        f'<span style="display:inline-block;padding:5px 12px;border-radius:999px;'
        f"background:{bg};color:{color};font-size:11px;font-weight:700;"
        f'letter-spacing:0.4px;text-transform:uppercase;">{label}</span>'
    )


def _section_label(text: str) -> str:
    return (
        f'<p style="margin:0 0 14px;font-size:12px;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{_C_GOLD};font-weight:700;">{text}</p>'
        f'<div style="height:2px;width:48px;background:linear-gradient(90deg,'
        f"{_C_GOLD_BRIGHT},transparent);margin:-8px 0 16px;border-radius:2px;\"></div>"
    )


def _wrap_email_document(title: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{_C_BG};font-family:{_C_FONT};">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{_C_BG};">
    <tr>
      <td align="center" style="padding:28px 14px;">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0"
               style="max-width:600px;width:100%;border-collapse:separate;border-spacing:0;">
          {content}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _email_header(
    *,
    gradient: str,
    border_color: str,
    eyebrow: str,
    title: str,
    subtitle: str,
    icon: str | None = None,
    image_src: str | None = None,
) -> str:
    icon_block = ""
    if image_src is not None:
        icon_block = (
            f'<img src="{image_src}" alt="Gold" width="132" '
            f'style="display:block;margin:0 auto 18px;border-radius:14px;'
            f'box-shadow:0 8px 24px rgba(0,0,0,0.45);">'
        )
    elif icon is not None:
        icon_block = (
            f'<p style="margin:0 0 14px;font-size:42px;line-height:1;">{icon}</p>'
        )
    return f"""
          <tr>
            <td style="padding:32px 28px;background:{gradient};border-radius:18px 18px 0 0;
                       border:1px solid {border_color};border-bottom:none;text-align:center;
                       box-shadow:0 4px 24px rgba(0,0,0,0.35);">
              {icon_block}
              <p style="margin:0 0 8px;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;
                        color:{_C_GOLD};font-family:{_C_FONT_UI};font-weight:600;">{eyebrow}</p>
              <h1 style="margin:0;font-size:30px;font-weight:700;color:#fff7e6;line-height:1.2;
                         text-shadow:0 2px 8px rgba(0,0,0,0.35);">{title}</h1>
              <p style="margin:10px 0 0;font-size:14px;color:#c4b58a;font-family:{_C_FONT_UI};">
                {subtitle}
              </p>
            </td>
          </tr>"""


def _email_footer(timestamp: str, *, note: str, extra: str = "") -> str:
    return f"""
          <tr>
            <td style="padding:22px 28px;background:{_C_PANEL};border:1px solid {_C_BORDER};
                       border-top:none;border-radius:0 0 18px 18px;text-align:center;">
              <p style="margin:0;font-size:12px;color:{_C_MUTED};line-height:1.7;
                        font-family:{_C_FONT_UI};">
                {timestamp}<br>{note}
              </p>
              {extra}
            </td>
          </tr>"""


def _detail_card(rows: list[tuple[str, str]], *, accent: str = _C_GOLD_BRIGHT) -> str:
    row_html = "".join(
        f'<tr>'
        f'<td style="padding:10px 0;border-bottom:1px solid {_C_BORDER};color:{_C_MUTED};'
        f'font-size:12px;text-transform:uppercase;letter-spacing:0.5px;width:42%;'
        f'font-family:{_C_FONT_UI};">{label}</td>'
        f'<td style="padding:10px 0;border-bottom:1px solid {_C_BORDER};color:{_C_TEXT};'
        f'font-size:14px;font-weight:600;text-align:right;font-family:{_C_FONT_UI};">'
        f"{value}</td></tr>"
        for label, value in rows
    )
    return f"""
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                     style="border-collapse:collapse;background:{_C_PANEL};border-radius:14px;
                            overflow:hidden;border:1px solid {_C_BORDER};border-left:4px solid {accent};">
                {row_html}
              </table>"""

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
        return f"Today is at a trailing low of {breach.horizon_label}"
    return "Today is not at a trailing low"


def _status_detail(breach: WindowBreach | None, current_usd: str) -> str:
    if breach is not None:
        return f"Price is lowest in the last {breach.horizon_label}."
    return "Price is above the minimum on every evaluated window."


def _daily_subject(
    latest: TradingDayClose,
    breach: WindowBreach | None,
    india_quote: IndiaGoldQuote | None = None,
) -> str:
    current_usd = format_usd(latest.close)
    parts = [f"🪙 Gold Daily: {current_usd}"]
    if india_quote is not None:
        parts[0] += f", ~{format_inr(india_quote.retail_per_10g)}"
    if breach is not None:
        return f"{parts[0]} — lowest in {breach.horizon_label}"
    if india_quote is not None:
        return parts[0]
    return f"{parts[0]} — Not at trailing low"


def _alert_badge(breach: WindowBreach | None) -> tuple[str, str, str, str, str]:
    if breach is not None:
        return (
            "#b45309",
            "#fde047",
            "#fffbeb",
            f"LOWEST IN {breach.horizon_label.upper()}",
            "0 0 32px rgba(251,191,36,0.6)",
        )
    return (
        "#14532d",
        "#86efac",
        "#ecfdf5",
        "✓ NOT AT LOW",
        "0 0 20px rgba(134,239,172,0.15)",
    )


def _format_retail_headline_html(quote: IndiaGoldQuote | None) -> str:
    if quote is None:
        return ""
    return f"""
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                     style="margin-top:22px;border-collapse:separate;border-spacing:0;">
                <tr>
                  <td width="50%" style="padding:16px 10px 16px 0;vertical-align:top;">
                    <div style="padding:18px 14px;background:{_C_PANEL};border-radius:14px;
                                border:1px solid {_C_BORDER};text-align:center;">
                      <p style="margin:0 0 6px;font-size:11px;letter-spacing:1px;text-transform:uppercase;
                                color:{_C_MUTED};font-family:{_C_FONT_UI};">India Retail Est.</p>
                      <p style="margin:0;font-size:28px;line-height:1.15;font-weight:700;color:{_C_GOLD_BRIGHT};">
                        ~ {format_inr(quote.retail_per_10g)}
                      </p>
                      <p style="margin:6px 0 0;font-size:11px;color:{_C_MUTED};">per 10g · 24K</p>
                    </div>
                  </td>
                  <td width="50%" style="padding:16px 0 16px 10px;vertical-align:top;">
                    <div style="padding:18px 14px;background:{_C_PANEL};border-radius:14px;
                                border:1px solid {_C_BORDER};text-align:center;">
                      <p style="margin:0 0 6px;font-size:11px;letter-spacing:1px;text-transform:uppercase;
                                color:{_C_MUTED};font-family:{_C_FONT_UI};">Intl. Parity</p>
                      <p style="margin:0;font-size:28px;line-height:1.15;font-weight:700;color:#fde68a;">
                        {format_inr(quote.parity_per_10g)}
                      </p>
                      <p style="margin:6px 0 0;font-size:11px;color:{_C_MUTED};">per 10g · spot FX</p>
                    </div>
                  </td>
                </tr>
              </table>"""


def _format_india_quote_html(quote: IndiaGoldQuote | None) -> str:
    if quote is None:
        return ""
    duty_pct = int(quote.import_duty_rate * 100)
    premium_pct = int(quote.local_premium_rate * 100)
    return f"""
              <div style="margin-top:22px;padding:20px 22px;background:linear-gradient(135deg,#1a1a28 0%,{_C_PANEL} 100%);
                          border-radius:14px;border:1px solid {_C_BORDER};border-left:4px solid {_C_GOLD};text-align:left;">
                {_section_label("India 24K Reference")}
                <p style="margin:0 0 14px;font-size:13px;color:{_C_MUTED};line-height:1.6;font-family:{_C_FONT_UI};">
                  Spot: {format_usd(quote.gold_usd_per_oz)}/oz → {format_usd(quote.usd_per_10g)}/10g
                  @ ₹{quote.usd_inr_rate:.2f}/USD
                </p>
                {_detail_card([
                    ("International parity", f"{format_inr(quote.parity_per_10g)} / 10g"),
                    ("Approx. India retail", f"{format_inr(quote.retail_per_10g)} / 10g"),
                    ("Per gram (retail)", format_inr(quote.retail_per_gram)),
                ])}
                <p style="margin:14px 0 0;font-size:11px;color:{_C_MUTED};line-height:1.6;font-family:{_C_FONT_UI};">
                  Includes +{duty_pct}% import duty + {premium_pct}% local premium.
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


def _window_status_pill(status: str, status_color: str) -> str:
    bg_map = {
        "#fbbf24": "#422006",
        "#86efac": "#14532d",
        "#9ca3af": "#1f2937",
    }
    bg = bg_map.get(status_color, "#1f2937")
    return _status_pill(status, status_color, bg)


def _window_rows_html(evaluations: list[WindowEvaluation]) -> str:
    rows: list[str] = []
    for index, evaluation in enumerate(evaluations):
        row_bg = "#14141f" if index % 2 == 0 else _C_PANEL
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
            f'<td style="padding:12px 14px;border-bottom:1px solid {_C_BORDER};'
            f'background:{row_bg};color:{_C_TEXT};font-size:14px;font-weight:600;">'
            f"{evaluation.horizon_label}</td>"
            f'<td style="padding:12px 14px;border-bottom:1px solid {_C_BORDER};'
            f'background:{row_bg};color:#cbd5e1;font-size:13px;font-family:{_C_FONT_UI};">'
            f"{detail}</td>"
            f'<td style="padding:12px 14px;border-bottom:1px solid {_C_BORDER};'
            f'background:{row_bg};text-align:right;">'
            f"{_window_status_pill(status, status_color)}</td>"
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
        f'<td style="padding:14px;background:linear-gradient(90deg,#1f1a0a,{_C_PANEL});'
        f'border-top:2px solid {_C_GOLD};color:{_C_GOLD_BRIGHT};font-size:14px;font-weight:700;">'
        f"Last 5 days</td>"
        f'<td style="padding:14px;background:linear-gradient(90deg,#1f1a0a,{_C_PANEL});'
        f'border-top:2px solid {_C_GOLD};color:#cbd5e1;font-size:13px;'
        f'font-family:{_C_FONT_UI};">{detail}</td>'
        f'<td style="padding:14px;background:linear-gradient(90deg,#1f1a0a,{_C_PANEL});'
        f'border-top:2px solid {_C_GOLD};text-align:right;">'
        f"{_window_status_pill(status, status_color)}</td>"
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
    if breach is not None:
        headline = _status_headline(breach)
        detail = _status_detail(breach, current_usd)
        alert_title = f"Lowest in {breach.horizon_label}"
    else:
        headline = _status_headline(breach)
        detail = _status_detail(breach, current_usd)
        alert_title = "Gold Price Alert"

    badge_bg, badge_border, badge_text_color, badge_text, badge_glow = _alert_badge(
        breach
    )

    ts = format_timestamp_ist(timestamp)

    fallback_note = ""
    if fallback_trading_days is not None:
        fallback_note = (
            f'<div style="margin-top:18px;padding:14px 16px;background:#422006;'
            f'border-radius:12px;border:1px solid #f59e0b;border-left:4px solid #fbbf24;">'
            f'<p style="margin:0;color:#fde68a;font-size:13px;line-height:1.6;font-family:{_C_FONT_UI};">'
            f"⚠️ <strong>Fallback data</strong> — {fallback_trading_days} trading days "
            f"(not full 1-year history).</p></div>"
        )

    action_html = ""
    if breach is not None:
        action_html = (
            f'<p style="margin:16px 0 0;font-size:14px;color:{_C_GOLD_BRIGHT};font-weight:700;'
            f'font-family:{_C_FONT_UI};">Action: Evaluate current entry positions.</p>'
        )

    retail_block = _format_retail_headline_html(india_quote)
    if india_quote is None:
        retail_block = ""

    inner = f"""
          {_email_header(
              gradient="linear-gradient(145deg,#4a3800 0%,#1a1408 48%,#080810 100%)",
              border_color="#6b5416",
              eyebrow="GC=F Daily Report",
              title=alert_title,
              subtitle=latest.date.strftime("%A, %d %B %Y"),
              image_src=GOLD_HEADER_IMAGE_SRC,
          )}
          <tr>
            <td style="padding:30px 28px;background:{_C_CARD};border-left:1px solid {_C_BORDER};
                       border-right:1px solid {_C_BORDER};text-align:center;">
              <div style="padding:22px 18px;background:linear-gradient(180deg,{_C_PANEL} 0%,#0f0f18 100%);
                          border-radius:16px;border:1px solid {_C_BORDER};
                          box-shadow:inset 0 1px 0 rgba(255,255,255,0.04);">
                <p style="margin:0 0 8px;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;
                          color:{_C_MUTED};font-family:{_C_FONT_UI};">Today's Close (GC=F)</p>
                <p style="margin:0;font-size:52px;line-height:1.05;font-weight:700;color:{_C_GOLD_BRIGHT};
                          text-shadow:0 2px 12px rgba(251,191,36,0.2);">{current_usd}</p>
              </div>
              {retail_block}
              <div style="display:inline-block;margin-top:24px;padding:12px 24px;background:{badge_bg};
                          border:2px solid {badge_border};border-radius:999px;color:{badge_text_color};
                          font-size:13px;font-weight:800;letter-spacing:1px;
                          box-shadow:{badge_glow};font-family:{_C_FONT_UI};">
                {badge_text}
              </div>
              <p style="margin:20px 0 0;font-size:17px;color:{_C_TEXT};line-height:1.55;font-weight:600;">
                {headline}
              </p>
              <p style="margin:8px 0 0;font-size:14px;color:#cbd5e1;line-height:1.6;font-family:{_C_FONT_UI};">
                {detail}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 28px 28px;background:{_C_CARD};border-left:1px solid {_C_BORDER};
                       border-right:1px solid {_C_BORDER};">
              {_section_label("Window Scan")}
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                     style="border-collapse:collapse;background:{_C_PANEL};border-radius:14px;
                            overflow:hidden;border:1px solid {_C_BORDER};">
                <tr>
                  <th align="left" style="padding:12px 14px;background:#1c1c2e;color:{_C_GOLD};
                      font-size:11px;text-transform:uppercase;letter-spacing:0.5px;
                      font-family:{_C_FONT_UI};">Window</th>
                  <th align="left" style="padding:12px 14px;background:#1c1c2e;color:{_C_GOLD};
                      font-size:11px;text-transform:uppercase;letter-spacing:0.5px;
                      font-family:{_C_FONT_UI};">Reference Low</th>
                  <th align="right" style="padding:12px 14px;background:#1c1c2e;color:{_C_GOLD};
                      font-size:11px;text-transform:uppercase;letter-spacing:0.5px;
                      font-family:{_C_FONT_UI};">Status</th>
                </tr>
                {_window_rows_html(evaluations)}
                {_last_five_summary_row_html(latest, recent_closes)}
              </table>
              {_format_india_quote_html(india_quote)}
              {fallback_note}
            </td>
          </tr>
          {_email_footer(
              ts,
              note="Source: Yahoo Finance GC=F · India estimates are indicative only.",
              extra=action_html,
          )}"""

    return _wrap_email_document("Gold Daily Report", inner)


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
    ts = format_timestamp_ist(timestamp)
    body = "\n".join(
        [
            "The Gold price alert engine could not fetch usable market data for GC=F.",
            "",
            f"Error: {CRITICAL_DATA_FETCH_ERROR}",
            f"Trading days received: {trading_days}",
            f"Retries exhausted: {MAX_RETRIES} attempts with {RETRY_DELAY_SECONDS}s delay",
            f"Timestamp: {ts}",
            "",
            "No low-detection was performed. Investigate Yahoo Finance connectivity or ticker availability.",
        ]
    )
    inner = f"""
          {_email_header(
              gradient="linear-gradient(145deg,#450a0a 0%,#1a0808 55%,#080810 100%)",
              border_color="#991b1b",
              eyebrow="System Alert",
              title="Critical Fetch Failure",
              subtitle="Gold alert engine could not load market data",
              icon="⛔",
          )}
          <tr>
            <td style="padding:28px;background:{_C_CARD};border-left:1px solid {_C_BORDER};
                       border-right:1px solid {_C_BORDER};">
              {_section_label("Error Details")}
              {_detail_card([
                  ("Error code", CRITICAL_DATA_FETCH_ERROR),
                  ("Trading days received", str(trading_days)),
                  ("Retries", f"{MAX_RETRIES} × {RETRY_DELAY_SECONDS}s delay"),
              ], accent="#ef4444")}
              <p style="margin:18px 0 0;font-size:14px;color:#fca5a5;line-height:1.7;
                        font-family:{_C_FONT_UI};">
                No trailing-low analysis was performed. Check Yahoo Finance connectivity,
                ticker availability (GC=F), and network access from the deployment host.
              </p>
            </td>
          </tr>
          {_email_footer(ts, note="Gold Price Alert Engine · automated system message")}"""
    body_html = _wrap_email_document("Critical Fetch Failure", inner)
    return AlertMessage(subject=subject, body=body, body_html=body_html)


def render_fallback_alert(
    trading_days: int,
    timestamp: datetime,
) -> AlertMessage:
    skipped = skipped_window_labels(trading_days)
    skipped_text = ", ".join(skipped) if skipped else "none"
    subject = f"⚠️ GOLD ALERT ENGINE: Running on Fallback Data ({trading_days} days)"
    ts = format_timestamp_ist(timestamp)
    body = "\n".join(
        [
            "Yahoo Finance returned incomplete history for GC=F.",
            "",
            f"Expected: {EXPECTED_TRADING_DAYS} trading days (~1 calendar year)",
            f"Received: {trading_days} trading days",
            "Mode: FALLBACK — using available recent days only",
            f"Skipped windows: {skipped_text}",
            f"Timestamp: {ts}",
            "",
            "Low-detection will proceed top-down for eligible windows (first match wins). "
            "The daily gold report follows with today's price and window scan.",
        ]
    )
    inner = f"""
          {_email_header(
              gradient="linear-gradient(145deg,#78350f 0%,#1a1208 55%,#080810 100%)",
              border_color="#d97706",
              eyebrow="Degraded Data Mode",
              title="Fallback Data Active",
              subtitle="Incomplete history — analysis uses recent days only",
              icon="⚠️",
          )}
          <tr>
            <td style="padding:28px;background:{_C_CARD};border-left:1px solid {_C_BORDER};
                       border-right:1px solid {_C_BORDER};">
              {_section_label("Data Summary")}
              {_detail_card([
                  ("Expected days", f"~{EXPECTED_TRADING_DAYS} trading days"),
                  ("Received days", str(trading_days)),
                  ("Mode", "FALLBACK"),
                  ("Skipped windows", skipped_text),
              ], accent="#f59e0b")}
              <p style="margin:18px 0 0;font-size:14px;color:#fde68a;line-height:1.7;
                        font-family:{_C_FONT_UI};">
                Trailing-low checks continue top-down on eligible windows only.
                A full daily gold report follows this notice.
              </p>
            </td>
          </tr>
          {_email_footer(ts, note="Gold Price Alert Engine · automated system message")}"""
    body_html = _wrap_email_document("Fallback Data Active", inner)
    return AlertMessage(subject=subject, body=body, body_html=body_html)
