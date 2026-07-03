import pytest

from src.pricing import (
    GRAMS_PER_10G,
    IMPORT_DUTY_RATE,
    LOCAL_PREMIUM_RATE,
    TROY_OZ_GRAMS,
    build_india_gold_quote,
    format_india_gold_summary,
    format_inr,
    format_inr_per_10g_line,
    format_usd,
    usd_gold_to_inr_per_10g,
)


class TestUsdGoldToInrPer10g:
    def test_standard_conversion(self) -> None:
        gold_usd = 2000.0
        usd_inr = 83.0
        result = usd_gold_to_inr_per_10g(gold_usd, usd_inr)
        expected = (2000.0 / TROY_OZ_GRAMS) * GRAMS_PER_10G * 83.0
        assert result == pytest.approx(expected)

    def test_rejects_non_positive_inputs(self) -> None:
        with pytest.raises(ValueError):
            usd_gold_to_inr_per_10g(0, 83.0)
        with pytest.raises(ValueError):
            usd_gold_to_inr_per_10g(2000.0, 0)


class TestIndiaGoldQuote:
    def test_builds_parity_and_retail_per_10g(self) -> None:
        quote = build_india_gold_quote(4190.0, 95.19)
        assert quote.usd_per_10g == pytest.approx((4190.0 / TROY_OZ_GRAMS) * 10)
        assert quote.parity_per_10g == pytest.approx(
            usd_gold_to_inr_per_10g(4190.0, 95.19)
        )
        assert quote.parity_per_gram == pytest.approx(quote.parity_per_10g / 10)
        assert quote.retail_per_10g == pytest.approx(
            quote.parity_per_10g * (1 + IMPORT_DUTY_RATE) * (1 + LOCAL_PREMIUM_RATE)
        )
        assert quote.retail_per_gram == pytest.approx(quote.retail_per_10g / 10)

    def test_summary_includes_per_10g_and_per_gram(self) -> None:
        quote = build_india_gold_quote(4190.0, 95.19)
        summary = format_india_gold_summary(quote)
        assert "International parity:" in summary
        assert "India retail estimate:" in summary
        assert "/ 10g" in summary
        assert "/ g" in summary
        assert "10% import duty" in summary
        assert f"{int(LOCAL_PREMIUM_RATE * 100)}% local premium" in summary


class TestFormatting:
    def test_format_usd(self) -> None:
        assert format_usd(1945.2) == "$1,945.20"

    def test_format_inr(self) -> None:
        assert format_inr(111234.567) == "₹111,234.57"

    def test_format_inr_per_10g_line(self) -> None:
        line = format_inr_per_10g_line(2000.0, 83.0)
        assert line.startswith("India parity: ₹")
        assert "/ 10g" in line
        assert "24K international parity" in line
