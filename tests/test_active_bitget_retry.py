"""Tests for the actual Bitget adapter imported by app.py."""
import unittest
from unittest.mock import Mock, patch
import bitget_market_data as market


class ActiveBitgetRetryTests(unittest.TestCase):
    def test_nonfinite_retry_after_uses_bounded_backoff(self):
        for invalid in ("NaN", "Infinity", "-Infinity", "-1", "invalid"):
            with self.subTest(header=invalid):
                limited = Mock(status_code=429, headers={"Retry-After": invalid})
                ok = Mock(status_code=200, headers={})
                ok.json.return_value = {"code": "00000", "data": []}
                with patch.object(market.SESSION, "get", side_effect=[limited, ok]) as getter:
                    with patch.object(market.time, "sleep") as sleep:
                        with patch.object(market.time, "monotonic", return_value=100.0):
                            with patch.object(market, "_LAST_REQUEST", [0.0]):
                                self.assertEqual(market._get("/test", {}), [])
                self.assertEqual(getter.call_count, 2)
                self.assertIn(0.8, [call.args[0] for call in sleep.call_args_list])

    def test_valid_retry_after_is_capped(self):
        limited = Mock(status_code=429, headers={"Retry-After": "100"})
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": []}
        with patch.object(market.SESSION, "get", side_effect=[limited, ok]):
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        self.assertEqual(market._get("/test", {}), [])
        self.assertIn(4.0, [call.args[0] for call in sleep.call_args_list])


class ActiveBitgetTimestampTests(unittest.TestCase):
    def test_invalid_exchange_timestamp_rejected_before_pagination(self):
        for stamp in ("NaN", "Infinity", "-1", "900000.5", None):
            with self.subTest(timestamp=stamp):
                page = [[stamp, "100", "102", "98", "100", "10"]]
                with patch.object(market, "_get", return_value=page) as getter:
                    with self.assertRaisesRegex(ValueError, "캔들 시각"):
                        market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
                self.assertEqual(getter.call_count, 1)

if __name__ == "__main__":
    unittest.main()
