from __future__ import annotations

import logging
from collections.abc import Callable

from src.analyzer import analyze_lows
from src.fetcher import fetch_gold_closes
from src.models import AnalysisResult, FetchMode, FetchResult, RunResult
from src.pricing import fetch_usd_inr_rate, format_inr_per_10g_line

logger = logging.getLogger(__name__)


class GoldAlertService:
    def __init__(
        self,
        fetch_fn: Callable[[], FetchResult] = fetch_gold_closes,
        inr_fn: Callable[[], float | None] = fetch_usd_inr_rate,
    ) -> None:
        self._fetch = fetch_fn
        self._inr = inr_fn

    def run(self) -> RunResult:
        fetch = self._fetch()
        logger.info(
            "fetch complete mode=%s trading_days=%s",
            fetch.mode.value,
            fetch.trading_days,
        )

        if fetch.mode is FetchMode.HARD_FAILURE:
            return RunResult(fetch=fetch, analysis=AnalysisResult(breach=None))

        breach = analyze_lows(fetch.closes)
        analysis = AnalysisResult(breach=breach)

        if breach is None:
            logger.info("no trailing-low breach")
            return RunResult(fetch=fetch, analysis=analysis)

        logger.info(
            "breach window=%s horizon=%s current=%s previous_min=%s",
            breach.window_key,
            breach.horizon_label,
            breach.current,
            breach.previous_min,
        )

        inr_line = self._build_inr_line(breach.current)
        return RunResult(fetch=fetch, analysis=analysis, inr_line=inr_line)

    def _build_inr_line(self, gold_usd: float) -> str | None:
        rate = self._inr()
        if rate is None:
            logger.warning("INR=X unavailable; alert will use USD only")
            return None
        return format_inr_per_10g_line(gold_usd, rate)


def run_daily_analysis() -> RunResult:
    return GoldAlertService().run()
