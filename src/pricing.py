from __future__ import annotations

import logging
from dataclasses import dataclass

import yfinance as yf

logger = logging.getLogger(__name__)

TROY_OZ_GRAMS = 31.1035
GRAMS_PER_10G = 10.0
USD_INR_TICKER = "INR=X"
IMPORT_DUTY_RATE = 0.10
LOCAL_PREMIUM_RATE = 0.04

PARITY_DISCLAIMER = (
    "24K international parity per 10g (excl. import duty, GST, local premium)"
)

RETAIL_DISCLAIMER = (
    "Indicative India retail estimate (excl. GST & making charges)"
)


@dataclass(frozen=True)
class IndiaGoldQuote:
    gold_usd_per_oz: float
    usd_inr_rate: float
    usd_per_gram: float
    usd_per_10g: float
    parity_per_gram: float
    parity_per_10g: float
    retail_per_gram: float
    retail_per_10g: float
    import_duty_rate: float
    local_premium_rate: float


def usd_gold_to_inr_per_10g(gold_usd_per_troy_oz: float, usd_inr_rate: float) -> float:
    if gold_usd_per_troy_oz <= 0 or usd_inr_rate <= 0:
        raise ValueError("gold_usd_per_troy_oz and usd_inr_rate must be positive")
    return (gold_usd_per_troy_oz / TROY_OZ_GRAMS) * GRAMS_PER_10G * usd_inr_rate


def build_india_gold_quote(
    gold_usd_per_troy_oz: float,
    usd_inr_rate: float,
    *,
    import_duty_rate: float = IMPORT_DUTY_RATE,
    local_premium_rate: float = LOCAL_PREMIUM_RATE,
) -> IndiaGoldQuote:
    usd_per_gram = gold_usd_per_troy_oz / TROY_OZ_GRAMS
    usd_per_10g = usd_per_gram * GRAMS_PER_10G
    parity_per_10g = usd_gold_to_inr_per_10g(gold_usd_per_troy_oz, usd_inr_rate)
    parity_per_gram = parity_per_10g / GRAMS_PER_10G
    after_duty = parity_per_10g * (1 + import_duty_rate)
    retail_per_10g = after_duty * (1 + local_premium_rate)
    retail_per_gram = retail_per_10g / GRAMS_PER_10G
    return IndiaGoldQuote(
        gold_usd_per_oz=gold_usd_per_troy_oz,
        usd_inr_rate=usd_inr_rate,
        usd_per_gram=usd_per_gram,
        usd_per_10g=usd_per_10g,
        parity_per_gram=parity_per_gram,
        parity_per_10g=parity_per_10g,
        retail_per_gram=retail_per_gram,
        retail_per_10g=retail_per_10g,
        import_duty_rate=import_duty_rate,
        local_premium_rate=local_premium_rate,
    )


def format_usd(amount: float) -> str:
    return f"${amount:,.2f}"


def format_inr(amount: float) -> str:
    return f"₹{amount:,.2f}"


def format_inr_per_10g_line(gold_usd_per_troy_oz: float, usd_inr_rate: float) -> str:
    inr_per_10g = usd_gold_to_inr_per_10g(gold_usd_per_troy_oz, usd_inr_rate)
    return f"India parity: {format_inr(inr_per_10g)} / 10g ({PARITY_DISCLAIMER})"


def format_india_gold_summary(quote: IndiaGoldQuote) -> str:
    duty_pct = int(quote.import_duty_rate * 100)
    premium_pct = int(quote.local_premium_rate * 100)
    return "\n".join(
        [
            "India 24K reference (GC=F spot conversion):",
            (
                f"  Spot: {format_usd(quote.gold_usd_per_oz)}/oz "
                f"→ {format_usd(quote.usd_per_10g)}/10g "
                f"@ ₹{quote.usd_inr_rate:.2f}/USD"
            ),
            (
                f"  International parity: {format_inr(quote.parity_per_10g)} / 10g "
                f"({format_inr(quote.parity_per_gram)} / g)"
            ),
            (
                f"  India retail estimate: {format_inr(quote.retail_per_10g)} / 10g "
                f"({format_inr(quote.retail_per_gram)} / g)"
            ),
            (
                f"  = parity + {duty_pct}% import duty + {premium_pct}% local premium "
                f"({RETAIL_DISCLAIMER})"
            ),
        ]
    )


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
