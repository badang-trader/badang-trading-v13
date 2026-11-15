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

    def test_transient_503_recovers(self):
        busy = Mock(status_code=503, headers={})
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": ["ok"]}
        with patch.object(market.SESSION, "get", side_effect=[busy, ok]) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        self.assertEqual(market._get("/test", {}), ["ok"])
        self.assertEqual(getter.call_count, 2)
        self.assertIn(0.8, [call.args[0] for call in sleep.call_args_list])

    def test_persistent_503_fails_after_three_attempts(self):
        busy = Mock(status_code=503, headers={})
        busy.raise_for_status.side_effect = RuntimeError("HTTP 503")
        with patch.object(market.SESSION, "get", return_value=busy) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        with self.assertRaisesRegex(RuntimeError, "503"):
                            market._get("/test", {})
        self.assertEqual(getter.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_http_429_exhaustion_does_not_return_stale_data(self):
        limited = Mock(status_code=429, headers={"Retry-After": "0"})
        with patch.object(market.SESSION, "get", return_value=limited) as getter:
            with patch.object(market.time, "sleep"):
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        with self.assertRaisesRegex(ValueError, "HTTP 429"):
                            market._get("/test", {})
        self.assertEqual(getter.call_count, 3)

    def test_bitget_body_rate_limit_retries_then_recovers(self):
        limited = Mock(status_code=200, headers={})
        limited.json.return_value = {"code": "40015", "msg": "rate limit"}
        ok = Mock(status_code=200, headers={})
        ok.json.return_value = {"code": "00000", "data": ["fresh"]}
        with patch.object(market.SESSION, "get", side_effect=[limited, ok]) as getter:
            with patch.object(market.time, "sleep") as sleep:
                with patch.object(market.time, "monotonic", return_value=100.0):
                    with patch.object(market, "_LAST_REQUEST", [0.0]):
                        self.assertEqual(market._get("/test", {}), ["fresh"])
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

class ActiveBitgetContinuityTests(unittest.TestCase):
    STEP = 900_000

    def rows(self):
        return [[str(i*self.STEP), "100", "102", "98", "100", "10"]
                for i in range(10, 230)]

    def test_220_recent_contiguous_bars_return_with_disposable_marker(self):
        with patch.object(market, "_get", return_value=self.rows()) as getter:
            with patch.object(market.time, "time", return_value=230*self.STEP/1000):
                result = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 1)
        self.assertEqual(len(result["candles"][:-1]), 220)
        self.assertEqual(int(result["candles"][-1][0]), 230*self.STEP)

    def test_missing_recent_bar_cannot_be_fabricated(self):
        rows = [r for r in self.rows() if int(r[0]) != 220*self.STEP]
        with patch.object(market, "_get", side_effect=[rows, [], []]) as getter:
            with patch.object(market.time, "time", return_value=230*self.STEP/1000):
                with self.assertRaisesRegex(ValueError, "연속 확정봉 부족"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertGreaterEqual(getter.call_count, 2)

    def test_stale_history_rejected_even_when_contiguous(self):
        rows = self.rows()
        with patch.object(market, "_get", return_value=rows):
            with patch.object(market.time, "time", return_value=234*self.STEP/1000):
                with self.assertRaisesRegex(ValueError, "최근 확정봉 지연"):
                    market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])

    def test_real_history_page_repairs_missing_bar(self):
        rows = [r for r in self.rows() if int(r[0]) != 220*self.STEP]
        repaired = [r for r in self.rows() if int(r[0]) == 220*self.STEP]
        with patch.object(market, "_get", side_effect=[rows, [], repaired]) as getter:
            with patch.object(market.time, "time", return_value=230*self.STEP/1000):
                result = market.fastest_candles("BTCUSDT", "15m", exchanges=["bitget"])
        self.assertEqual(getter.call_count, 3)
        self.assertEqual(len(result["candles"][:-1]), 220)
        self.assertIn(str(220*self.STEP), [r[0] for r in result["candles"][:-1]])

if __name__ == "__main__":
    unittest.main()
