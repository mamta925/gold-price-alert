from __future__ import annotations

import logging
from collections.abc import Callable

from src.analyzer import analyze_lows
from src.fetcher import fetch_gold_closes
from src.models import AnalysisResult, FetchMode, FetchResult, RunResult
from src.pricing import build_india_gold_quote, fetch_usd_inr_rate

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
            "[2/5] Using fetch result: mode=%s trading_days=%s",
            fetch.mode.value,
            fetch.trading_days,
        )

        if fetch.mode is FetchMode.HARD_FAILURE:
            logger.warning("[3/5] Skipping analysis — hard fetch failure")
            return RunResult(fetch=fetch, analysis=AnalysisResult(breach=None))

        logger.info("[3/5] Analyzing trailing lows (top-down short-circuit)...")
        breach = analyze_lows(fetch.closes)
        analysis = AnalysisResult(breach=breach)

        if breach is None:
            latest = fetch.closes[-1]
            logger.info(
                "[3/5] Analysis complete: no breach (latest_close=%.2f) — daily report only",
                latest.close,
            )
        else:
            logger.info(
                "[3/5] Analysis complete: breach window=%s horizon=%s current=%.2f previous_min=%.2f",
                breach.window_key,
                breach.horizon_label,
                breach.current,
                breach.previous_min,
            )

        current = fetch.closes[-1].close
        logger.info("[3/5] Fetching INR=X for daily report...")
        india_quote = self._build_india_quote(current)
        return RunResult(fetch=fetch, analysis=analysis, india_quote=india_quote)

    def _build_india_quote(self, gold_usd: float):
        rate = self._inr()
        if rate is None:
            logger.warning("[3/5] INR=X unavailable — alert will use USD only")
            return None
        logger.info("[3/5] INR=X response: rate=%.4f", rate)
        quote = build_india_gold_quote(gold_usd, rate)
        logger.info(
            "[3/5] India 24K reference: parity=%.2f/10g retail_est=%.2f/10g",
            quote.parity_per_10g,
            quote.retail_per_10g,
        )
        return quote


def run_daily_analysis() -> RunResult:
    return GoldAlertService().run()
