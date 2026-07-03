from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.analyzer import evaluate_windows
from src.config import AppConfig, load_config
from src.fetcher import fetch_gold_closes
from src.models import FetchMode, FetchResult, RunResult
from src.notifier import DispatchResult, Notifier
from src.pricing import fetch_usd_inr_rate
from src.service import GoldAlertService
from src.templates import (
    render_daily_alert,
    render_fallback_alert,
    render_hard_failure_alert,
)

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
NowFn = Callable[[], datetime]
FetchFn = Callable[[], FetchResult]
InrFn = Callable[[], float | None]


@dataclass(frozen=True)
class JobResult:
    status: str
    run: RunResult | None
    notifications: tuple[DispatchResult, ...]

    def __repr__(self) -> str:
        return format_job_summary(self)


def format_job_summary(result: JobResult) -> str:
    parts = [f"status={result.status}"]
    if result.run is not None:
        run = result.run
        parts.append(f"should_alert={run.should_alert}")
        parts.append(f"fetch={run.fetch!r}")
        breach = run.analysis.breach
        if breach is not None:
            parts.append(f"breach={breach!r}")
        if run.inr_line:
            parts.append("inr_line=set")
    for index, note in enumerate(result.notifications):
        whatsapp_note = (
            f"whatsapp:{note.whatsapp_sent}"
            if note.whatsapp_sent
            else "whatsapp:FAILED (check logs / Twilio sandbox join)"
        )
        parts.append(f"notify[{index}]=email:{note.email_sent},{whatsapp_note}")
    return "JobResult(" + ", ".join(parts) + ")"


def configure_pipeline_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def run_daily_job(
    *,
    config: AppConfig | None = None,
    fetch_fn: FetchFn = fetch_gold_closes,
    inr_fn: InrFn = fetch_usd_inr_rate,
    notifier: Notifier | None = None,
    now_fn: NowFn | None = None,
) -> JobResult:
    configure_pipeline_logging()
    logger.info("=== Daily gold alert job started ===")
    cfg = config or load_config()
    notify = notifier or Notifier(cfg)
    timestamp = (now_fn or (lambda: datetime.now(tz=IST)))()

    fetch = fetch_fn()
    notifications: list[DispatchResult] = []

    if fetch.mode is FetchMode.HARD_FAILURE:
        logger.error("[3/5] Hard failure — sending critical email only")
        message = render_hard_failure_alert(fetch.trading_days, timestamp)
        notifications.append(notify.send_system_alert(message))
        logger.info("=== Job finished status=hard_failure ===")
        return JobResult(
            status="hard_failure",
            run=None,
            notifications=tuple(notifications),
        )

    if fetch.mode is FetchMode.FALLBACK:
        logger.warning("[3/5] Fallback mode — sending degraded-data email")
        message = render_fallback_alert(fetch.trading_days, timestamp)
        notifications.append(notify.send_system_alert(message))

    run = GoldAlertService(fetch_fn=lambda: fetch, inr_fn=inr_fn).run()
    breach = run.analysis.breach
    fallback_days = fetch.trading_days if fetch.mode is FetchMode.FALLBACK else None
    message = render_daily_alert(
        latest=fetch.closes[-1],
        breach=breach,
        window_evaluations=evaluate_windows(fetch.closes),
        india_quote=run.india_quote,
        recent_closes=fetch.closes[-5:],
        timestamp=timestamp,
        fallback_trading_days=fallback_days,
    )
    notifications.append(notify.send_price_alert(message))

    if breach is not None:
        status = "price_alert" if fetch.mode is FetchMode.FULL else "fallback_price_alert"
    elif fetch.mode is FetchMode.FALLBACK:
        status = "fallback_daily"
    else:
        status = "daily_report"

    logger.info("=== Job finished status=%s ===", status)
    return JobResult(
        status=status,
        run=run,
        notifications=tuple(notifications),
    )
