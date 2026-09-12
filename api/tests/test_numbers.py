import pytest
from app.utils.numbers import normalize_inr_amount


class TestNormalizeInrAmount:
    def test_crore_decimal(self):
        assert normalize_inr_amount("Rs. 1.45 crore") == 14_500_000

    def test_crore_words(self):
        assert normalize_inr_amount("Rupees one crore forty-five lakh only") == 14_500_000

    def test_indian_commas(self):
        assert normalize_inr_amount("₹1,45,00,000") == 14_500_000

    def test_lakh(self):
        assert normalize_inr_amount("14.5 lakh") == 1_450_000

    def test_monthly_to_annual(self):
        assert normalize_inr_amount("45 lakh a month") == 54_000_000

    def test_plain_inr_symbol(self):
        assert normalize_inr_amount("INR 10,00,000") == 1_000_000

    def test_aggregate_turnover_line(self):
        text = "Aggregate turnover declared for FY 2024-25: Rs. 1.45 crore (Rupees one crore forty-five lakh only)"
        assert normalize_inr_amount(text) == 14_500_000

    def test_empty_returns_none(self):
        assert normalize_inr_amount("") is None
        assert normalize_inr_amount("no numbers here") is None

    def test_large_plain_number(self):
        assert normalize_inr_amount("14500000") == 14_500_000
