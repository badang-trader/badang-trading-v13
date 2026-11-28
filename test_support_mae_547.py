"""Regression tests for fixed-horizon support adverse excursion."""
import unittest
from unittest.mock import patch
from badang_support_backtest_545 import support_touch_backtest

STEP = 900000

def sample():
    return [{"timestamp": i * STEP, "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 10} for i in range(105)]

def support(*args, **kwargs):
    return {"status": "ok", "zones": [{"status": "historical_support",
            "lower": 99, "upper": 100.5, "center": 100,
            "evidence_score": 70}]}

class MAETests(unittest.TestCase):
    def test_low_after_touch_included(self):
        data = sample()
        data[92]["low"] = 90
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=support):
            result = support_touch_backtest(
                data, "BTC", "15m", exchange_now_ms=105 * STEP)
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["events"][0]["max_adverse_excursion_pct"],
                               round((100.5-90)/100.5*100, 4))
        self.assertEqual(result["mean_max_adverse_excursion_pct"],
                         result["events"][0]["max_adverse_excursion_pct"])

    def test_no_touch_no_mae(self):
        data = sample()
        for bar in data:
            bar["low"] = 101
            bar["open"] = 102
            bar["high"] = 103
            bar["close"] = 102
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=support):
            result = support_touch_backtest(
                data, "ETH", "15m", exchange_now_ms=105 * STEP)
        self.assertEqual(result["events"], [])
        self.assertIsNone(result["mean_max_adverse_excursion_pct"])

if __name__ == "__main__":
    unittest.main()
