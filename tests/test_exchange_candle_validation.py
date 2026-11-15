"""Offline checks for exchange candle validation. No API calls or orders."""
import unittest
from unittest.mock import patch
from exchange_data import validate_candles

STEP = 900_000

def sample_rows(n=205):
    return [[i * STEP, 100.0, 102.0, 98.0, 100.0, 10.0, 1000.0]
            for i in range(1, n + 1)]

class ExchangeCandleValidationTests(unittest.TestCase):
    def test_valid_completed_contiguous_rows(self):
        rows = sample_rows()
        with patch("exchange_data.time.time", return_value=(207 * STEP) / 1000):
            result = validate_candles(rows, "15m")
        self.assertEqual(len(result), 205)

    def test_nonfinite_prices_cannot_pass_minimum(self):
        for column, value in ((1, float("nan")), (2, float("inf")),
                              (3, -float("inf")), (4, float("nan")),
                              (5, float("nan"))):
            with self.subTest(column=column):
                rows = sample_rows()
                rows[10][column] = value
                with patch("exchange_data.time.time", return_value=(207 * STEP) / 1000):
                    with self.assertRaisesRegex(ValueError, "insufficient"):
                        validate_candles(rows, "15m")

    def test_fractional_timestamp_rejected(self):
        rows = sample_rows()
        rows[10][0] += 0.5
        with patch("exchange_data.time.time", return_value=(207 * STEP) / 1000):
            with self.assertRaisesRegex(ValueError, "insufficient"):
                validate_candles(rows, "15m")

if __name__ == "__main__":
    unittest.main()
