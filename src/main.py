from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import AppConfig, load_config
from src.fetcher import fetch_gold_closes
from src.models import FetchMode, FetchResult, RunResult
from src.notifier import DispatchResult, Notifier
from src.pricing import fetch_usd_inr_rate
from src.service import GoldAlertService
from src.templates import (
    render_fallback_alert,
    render_hard_failure_alert,
    render_price_alert,
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


def run_daily_job(
    *,
    config: AppConfig | None = None,
    fetch_fn: FetchFn = fetch_gold_closes,
    inr_fn: InrFn = fetch_usd_inr_rate,
    notifier: Notifier | None = None,
    now_fn: NowFn | None = None,
) -> JobResult:
    cfg = config or load_config()
    notify = notifier or Notifier(cfg)
    timestamp = (now_fn or (lambda: datetime.now(tz=IST)))()

    fetch = fetch_fn()
    notifications: list[DispatchResult] = []

    if fetch.mode is FetchMode.HARD_FAILURE:
        logger.error("hard failure trading_days=%s", fetch.trading_days)
        message = render_hard_failure_alert(fetch.trading_days, timestamp)
        notifications.append(notify.send_system_alert(message))
        return JobResult(
            status="hard_failure",
            run=None,
            notifications=tuple(notifications),
        )

    if fetch.mode is FetchMode.FALLBACK:
        logger.warning("fallback mode trading_days=%s", fetch.trading_days)
        message = render_fallback_alert(fetch.trading_days, timestamp)
        notifications.append(notify.send_system_alert(message))

    run = GoldAlertService(fetch_fn=lambda: fetch, inr_fn=inr_fn).run()

    if not run.should_alert:
        status = "fallback_silent" if fetch.mode is FetchMode.FALLBACK else "silent"
        logger.info("no price alert status=%s", status)
        return JobResult(status=status, run=run, notifications=tuple(notifications))

    breach = run.analysis.breach
    assert breach is not None
    fallback_days = (
        fetch.trading_days if fetch.mode is FetchMode.FALLBACK else None
    )
    message = render_price_alert(
        breach,
        inr_line=run.inr_line,
        timestamp=timestamp,
        fallback_trading_days=fallback_days,
    )
    logger.info("price alert window=%s", breach.window_key)
    notifications.append(notify.send_price_alert(message))
    return JobResult(
        status="price_alert",
        run=run,
        notifications=tuple(notifications),
    )
