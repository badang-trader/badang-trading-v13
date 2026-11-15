"""Offline checks for exchange candle validation. No API calls or orders."""
import unittest
from unittest.mock import patch, Mock
from exchange_data import validate_candles, get_json

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

class ExchangeRetryTests(unittest.TestCase):
    def test_429_retries_and_recovers(self):
        throttled = Mock(status_code=429, headers={"Retry-After": "0"})
        success = Mock(status_code=200, headers={})
        success.json.return_value = {"code": "00000"}
        with patch("exchange_data.SESSION.get", side_effect=[throttled, success]) as get:
            with patch("exchange_data.time.sleep") as sleep:
                self.assertEqual(get_json("https://api.bitget.com/test"), {"code": "00000"})
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(0.0)

    def test_429_stops_after_three_attempts(self):
        throttled = Mock(status_code=429, headers={})
        throttled.raise_for_status.side_effect = RuntimeError("429")
        with patch("exchange_data.SESSION.get", return_value=throttled) as get:
            with patch("exchange_data.time.sleep") as sleep:
                with self.assertRaisesRegex(RuntimeError, "429"):
                    get_json("https://api.bitget.com/test")
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_nonretryable_error_does_not_retry(self):
        bad = Mock(status_code=400, headers={})
        bad.raise_for_status.side_effect = RuntimeError("400")
        with patch("exchange_data.SESSION.get", return_value=bad) as get:
            with patch("exchange_data.time.sleep") as sleep:
                with self.assertRaisesRegex(RuntimeError, "400"):
                    get_json("https://api.bitget.com/test")
        self.assertEqual(get.call_count, 1)
        sleep.assert_not_called()

if __name__ == "__main__":
    unittest.main()
