"""Regression checks for support reliability evidence and invalidation."""
import unittest
from badang_support_reliability_543 import (
    evaluate_support_reliability, multi_timeframe_reliability)


def candles(n=120):
    result = []
    for i in range(n):
        p = 100 + i * .02 - (3 if i % 15 == 7 else 0)
        result.append({"open": p, "high": p+1, "low": p-1,
                       "close": p, "volume": 100})
    return result


class ReliabilityTests(unittest.TestCase):
    def test_scores_not_probabilities(self):
        result = evaluate_support_reliability(candles(), "BTC", "15m")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["trading_ready"])
        for zone in result["zones"]:
            self.assertTrue(0 <= zone["evidence_score"] <= 100)
            self.assertIsNone(zone["rebound_probability"])

    def test_broken_level_not_high_confidence(self):
        data = candles()
        # A historical low has been breached on a later confirmed candle.
        data[-1] = {"open": 94, "high": 95, "low": 93, "close": 94, "volume": 100}
        result = evaluate_support_reliability(data, "ETH", "1h")
        self.assertEqual(result["status"], "ok")
        for zone in result["zones"]:
            if zone["confirmed_close_breaches"]:
                self.assertEqual(zone["status"], "broken")
                self.assertEqual(zone["evidence_grade"], "invalidated")

    def test_invalid_middle_bar(self):
        data = candles()
        data[30]["low"] = -1
        self.assertEqual(evaluate_support_reliability(data, "BTC", "15m")["status"],
                         "invalid_data")

    def test_unconfirmed_rejected(self):
        self.assertEqual(evaluate_support_reliability(
            candles(), "BTC", "15m", confirmed=False)["zones"], [])

    def test_swing_timeframes(self):
        self.assertEqual(set(multi_timeframe_reliability({}, "ETH", "swing")),
                         {"1h", "4h", "1d"})

    def test_no_unsupported_coin(self):
        with self.assertRaises(ValueError):
            evaluate_support_reliability(candles(), "SOL", "15m")


if __name__ == "__main__":
    unittest.main()
