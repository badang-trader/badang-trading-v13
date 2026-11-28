"""Offline tests for Bitget derivatives data quality; no live API or orders."""
import unittest
from unittest.mock import patch
import bitget_market_data as market


class DerivativesQualityTests(unittest.TestCase):
    def snapshot(self, oi, funding):
        with patch.object(market, "_get", side_effect=[
            {"openInterest": oi},
            [{"fundingRate": funding}],
        ]):
            return market.bitget_derivatives_snapshot("BTCUSDT", [])

    def test_nonfinite_oi_is_not_reported_as_valid(self):
        for value in ("NaN", "Infinity", "-Infinity", "-1"):
            with self.subTest(oi=value):
                result = self.snapshot(value, "0.0001")
                self.assertIsNone(result["oi_contracts"])
                self.assertEqual(result["errors"].get("oi"), "ValueError")
                self.assertEqual(result["funding_rate"], 0.0001)

    def test_nonfinite_funding_is_not_reported_as_valid(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(funding=value):
                result = self.snapshot("1234", value)
                self.assertIsNone(result["funding_rate"])
                self.assertEqual(result["errors"].get("funding"), "ValueError")
                self.assertEqual(result["oi_contracts"], 1234.0)

    def test_zero_open_interest_is_preserved(self):
        result = self.snapshot(0, "0")
        self.assertEqual(result["oi_contracts"], 0.0)
        self.assertEqual(result["funding_rate"], 0.0)
        self.assertEqual(result["errors"], {})

    def test_valid_values_preserved(self):
        result = self.snapshot("1234.5", "-0.0002")
        self.assertEqual(result["oi_contracts"], 1234.5)
        self.assertEqual(result["funding_rate"], -0.0002)
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertFalse(result["eligible_for_alert"])


if __name__ == "__main__":
    unittest.main()
