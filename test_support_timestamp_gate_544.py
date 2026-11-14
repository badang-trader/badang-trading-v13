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
