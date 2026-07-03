from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date

import pandas as pd
import yfinance as yf

from src.models import (
    CRITICAL_DATA_FETCH_ERROR,
    DATA_FETCH_DEGRADED,
    EXPECTED_TRADING_DAYS,
    FALLBACK_MIN_DAYS,
    FetchMode,
    FetchResult,
    TradingDayClose,
)

logger = logging.getLogger(__name__)


def classify_mode(count: int) -> tuple[FetchMode, str | None, str | None]:
    if count >= EXPECTED_TRADING_DAYS:
        return FetchMode.FULL, None, None
    if count >= FALLBACK_MIN_DAYS:
        return FetchMode.FALLBACK, None, DATA_FETCH_DEGRADED
    return FetchMode.HARD_FAILURE, CRITICAL_DATA_FETCH_ERROR, None


def normalize_closes(df: pd.DataFrame) -> list[TradingDayClose]:
    if df.empty or "Close" not in df.columns:
        return []

    working = df[["Close"]].copy()
    working = working[~working["Close"].isna()]
    working = working[working["Close"] > 0]
    if working.empty:
        return []

    working = working[~working.index.duplicated(keep="last")]
    working = working.sort_index()

    closes: list[TradingDayClose] = []
    for ts, row in working.iterrows():
        session_date = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
        closes.append(TradingDayClose(date=session_date, close=float(row["Close"])))
    return closes


def _fetch_history(ticker: str, period: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)


def _build_result(closes: list[TradingDayClose]) -> FetchResult:
    mode, error_code, degraded_code = classify_mode(len(closes))
    if mode is FetchMode.HARD_FAILURE:
        return FetchResult(
            mode=mode,
            trading_days=0,
            closes=[],
            error_code=error_code,
            degraded_code=degraded_code,
        )
    return FetchResult(
        mode=mode,
        trading_days=len(closes),
        closes=closes,
        error_code=error_code,
        degraded_code=degraded_code,
    )


def fetch_gold_closes(
    *,
    ticker: str = "GC=F",
    period: str = "1y",
    max_retries: int = 3,
    retry_delay_seconds: int = 60,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> FetchResult:
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "[1/5] Fetching %s from Yahoo Finance (attempt %s/%s, period=%s)...",
                ticker,
                attempt,
                max_retries,
                period,
            )
            df = _fetch_history(ticker, period)
            closes = normalize_closes(df)

            if not closes:
                logger.warning(
                    "[1/5] Fetch returned no valid closes (attempt %s/%s)",
                    attempt,
                    max_retries,
                )
                if attempt < max_retries:
                    logger.info("[1/5] Retrying in %ss...", retry_delay_seconds)
                    sleep_fn(retry_delay_seconds)
                    continue
                break

            result = _build_result(closes)
            latest = closes[-1]
            logger.info(
                "[2/5] Fetch response: mode=%s trading_days=%s latest_close=%.2f date=%s",
                result.mode.value,
                result.trading_days,
                latest.close,
                latest.date,
            )
            if result.mode is FetchMode.HARD_FAILURE:
                logger.warning(
                    "[2/5] Insufficient data for analysis (rows=%s, minimum=%s)",
                    len(closes),
                    FALLBACK_MIN_DAYS,
                )
            elif result.mode is FetchMode.FALLBACK:
                logger.warning(
                    "[2/5] Fallback data: received=%s expected=%s",
                    result.trading_days,
                    EXPECTED_TRADING_DAYS,
                )
            return result

        except Exception as exc:
            last_error = exc
            logger.warning(
                "[1/5] Fetch error on attempt %s/%s: %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                logger.info("[1/5] Retrying in %ss...", retry_delay_seconds)
                sleep_fn(retry_delay_seconds)

    logger.error(
        "[2/5] Fetch failed after %s attempts: %s",
        max_retries,
        last_error or "empty_data",
    )
    return FetchResult(
        mode=FetchMode.HARD_FAILURE,
        trading_days=0,
        closes=[],
        error_code=CRITICAL_DATA_FETCH_ERROR,
    )
