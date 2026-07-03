import pytest

from src.pricing import (
    GRAMS_PER_10G,
    TROY_OZ_GRAMS,
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
