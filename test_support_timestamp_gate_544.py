"""Regression tests: never score support on unclosed or gapped candles."""
import unittest
from badang_support_timestamp_gate_544 import validated_support_reliability

STEP = 900000


def bars(n=120):
    out = []
    for i in range(n):
        p = 100 + .02 * i - (3 if i % 15 == 7 else 0)
        out.append({"timestamp": i * STEP, "open": p,
                    "high": p + 1, "low": p - 1,
                    "close": p, "volume": 100})
    return out


class TimestampGateTests(unittest.TestCase):
    def test_invalid_timeframe_types_rejected(self):
        for timeframe in (None, [], {}, 123, True, ""):
            with self.subTest(timeframe=timeframe):
                with self.assertRaises(ValueError):
                    validated_support_reliability(
                        bars(), "BTC", timeframe,
                        exchange_now_ms=120*STEP)

    def test_exchange_clock_must_be_finite_epoch_milliseconds(self):
        for clock in (None, True, float("nan"), float("inf"),
                      120*STEP - 0.5, "not-a-timestamp"):
            with self.subTest(clock=clock):
                with self.assertRaises(ValueError):
                    validated_support_reliability(
                        bars(), "BTC", "15m", exchange_now_ms=clock)

    def test_all_bitget_timeframes_require_closed_contiguous_bars(self):
        intervals = {"15m": 900000, "30m": 1800000,
                     "1h": 3600000, "4h": 14400000,
                     "1d": 86400000}
        for timeframe, interval in intervals.items():
            mode = "swing" if timeframe in ("4h", "1d") else "scalp"
            with self.subTest(timeframe=timeframe):
                data = bars()
                for i, row in enumerate(data):
                    row["timestamp"] = i * interval
                result = validated_support_reliability(
                    data, "BTC", timeframe, mode,
                    exchange_now_ms=len(data)*interval)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["timestamp_integrity"], "verified")

                data[40]["timestamp"] += interval
                broken = validated_support_reliability(
                    data, "BTC", timeframe, mode,
                    exchange_now_ms=len(data)*interval)
                self.assertEqual(broken["status"], "noncontiguous_history")
                self.assertFalse(broken["trading_ready"])

                data[40]["timestamp"] -= interval
                open_bar = validated_support_reliability(
                    data, "BTC", timeframe, mode,
                    exchange_now_ms=len(data)*interval-1)
                self.assertEqual(open_bar["status"], "open_or_future_candle")

    def test_short_history_does_not_hide_invalid_symbol_or_mode(self):
        for symbol, timeframe, mode in (
            ("SOL", "15m", "scalp"),
            (None, "15m", "scalp"),
            ("BTC", "1d", "scalp"),
            ("BTC", "15m", "swing"),
            ("BTC", "15m", None),
            ("BTC", "15m", []),
        ):
            with self.subTest(symbol=symbol, timeframe=timeframe, mode=mode):
                with self.assertRaises(ValueError):
                    validated_support_reliability(
                        bars(10), symbol, timeframe, mode,
                        exchange_now_ms=120*STEP)

    def test_short_history_does_not_bypass_exchange_clock_validation(self):
        for clock in (None, True, -1, float("nan"), "invalid"):
            with self.subTest(clock=clock):
                with self.assertRaises(ValueError):
                    validated_support_reliability(
                        bars(10), "BTC", "15m", exchange_now_ms=clock)
        result = validated_support_reliability(
            bars(10), "BTC", "15m", exchange_now_ms=120*STEP)
        self.assertEqual(result["status"], "insufficient_history")

    def test_closed_contiguous(self):
        data = bars()
        r = validated_support_reliability(data, "BTC", "15m",
                                          exchange_now_ms=len(data)*STEP)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["timestamp_integrity"], "verified")

    def test_open_bar_rejected(self):
        data = bars()
        r = validated_support_reliability(data, "ETH", "15m",
                                          exchange_now_ms=len(data)*STEP-1)
        self.assertEqual(r["status"], "open_or_future_candle")

    def test_missing_bar_rejected(self):
        data = bars()
        data.pop(40)
        r = validated_support_reliability(data, "BTC", "15m",
                                          exchange_now_ms=120*STEP)
        self.assertEqual(r["status"], "noncontiguous_history")

    def test_duplicate_rejected(self):
        data = bars()
        data[40]["timestamp"] = data[39]["timestamp"]
        r = validated_support_reliability(data, "BTC", "15m",
                                          exchange_now_ms=120*STEP)
        self.assertEqual(r["status"], "noncontiguous_history")

    def test_misaligned_rejected(self):
        data = bars()
        data[40]["timestamp"] += 1
        r = validated_support_reliability(data, "BTC", "15m",
                                          exchange_now_ms=120*STEP)
        self.assertEqual(r["status"], "misaligned_timestamp")

    def test_missing_timestamp_rejected(self):
        data = bars()
        del data[40]["timestamp"]
        r = validated_support_reliability(data, "BTC", "15m",
                                          exchange_now_ms=120*STEP)
        self.assertEqual(r["status"], "invalid_timestamp")


if __name__ == "__main__":
    unittest.main()
