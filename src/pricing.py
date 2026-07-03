from __future__ import annotations

import logging

import yfinance as yf

logger = logging.getLogger(__name__)

TROY_OZ_GRAMS = 31.1035
GRAMS_PER_10G = 10.0
USD_INR_TICKER = "INR=X"

PARITY_DISCLAIMER = (
    "24K international parity per 10g (excl. import duty, GST, local premium)"
)


def usd_gold_to_inr_per_10g(gold_usd_per_troy_oz: float, usd_inr_rate: float) -> float:
    if gold_usd_per_troy_oz <= 0 or usd_inr_rate <= 0:
        raise ValueError("gold_usd_per_troy_oz and usd_inr_rate must be positive")
    return (gold_usd_per_troy_oz / TROY_OZ_GRAMS) * GRAMS_PER_10G * usd_inr_rate


def format_usd(amount: float) -> str:
    return f"${amount:,.2f}"


def format_inr(amount: float) -> str:
    return f"₹{amount:,.2f}"


def format_inr_per_10g_line(gold_usd_per_troy_oz: float, usd_inr_rate: float) -> str:
    inr_per_10g = usd_gold_to_inr_per_10g(gold_usd_per_troy_oz, usd_inr_rate)
    return f"India parity: {format_inr(inr_per_10g)} / 10g ({PARITY_DISCLAIMER})"


def fetch_usd_inr_rate() -> float | None:
    try:
        history = yf.Ticker(USD_INR_TICKER).history(period="5d")
        if history.empty or "Close" not in history.columns:
            logger.warning("INR=X fetch returned empty data")
            return None
        rate = float(history["Close"].dropna().iloc[-1])
        if rate <= 0:
            return None
        return rate
    except Exception:
        logger.warning("INR=X fetch failed", exc_info=True)
        return None
