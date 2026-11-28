"""Tests that pre-outcome MAE stops at first confirmed rebound."""
import unittest
from unittest.mock import patch
from badang_support_backtest_545 import support_touch_backtest

STEP = 900000

def sample():
    return [{"timestamp": i*STEP, "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 100} for i in range(105)]

def zones(*args, **kwargs):
    return {"status": "ok", "zones": [{"status": "historical_support",
        "lower": 99, "upper": 100.5, "center": 100,
        "evidence_score": 75}]}

class PreOutcomeMAETests(unittest.TestCase):
    def test_rebound_then_later_drop_is_not_pre_rebound_mae(self):
        data = sample()
        data[91]["high"] = 103
        data[91]["close"] = 102
        data[92]["low"] = 90
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=zones):
            r = support_touch_backtest(
                data, "BTC", "15m", exchange_now_ms=105*STEP)
        e = r["events"][0]
        self.assertEqual(e["outcome"], "rebound")
        self.assertEqual(e["outcome_bar_index"], 91)
        self.assertLess(e["pre_outcome_max_adverse_excursion_pct"],
                        e["max_adverse_excursion_pct"])

    def test_touch_bar_breakdown_stops_immediately(self):
        data = sample()
        data[90]["low"] = 96
        data[90]["close"] = 98
        data[92]["low"] = 85
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=zones):
            r = support_touch_backtest(
                data, "ETH", "15m", exchange_now_ms=105*STEP)
        e = r["events"][0]
        self.assertEqual(e["outcome"], "breakdown_on_touch")
        self.assertEqual(e["outcome_bar_index"], 90)
        self.assertLess(e["pre_outcome_max_adverse_excursion_pct"],
                        e["max_adverse_excursion_pct"])

if __name__ == "__main__":
    unittest.main()
