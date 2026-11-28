"""Outcome-specific MAE summaries must not conflate rebounds and breakdowns."""
import unittest
from unittest.mock import patch
from badang_support_backtest_545 import support_touch_backtest

STEP = 900000

def fixture():
    return [{"timestamp": i*STEP, "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 100} for i in range(125)]

def mock_zones(*args, **kwargs):
    return {"status": "ok", "zones": [{"status": "historical_support",
        "lower": 99, "upper": 100.5, "center": 100, "evidence_score": 75}]}

class MAEOutcomeTests(unittest.TestCase):
    def test_rebound_and_breakdown_reported_separately(self):
        data = fixture()
        data[91]["high"], data[91]["close"] = 103, 102
        # Next independent touch window starts at bar 99.
        data[99]["low"], data[99]["close"] = 96, 98
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=mock_zones):
            r = support_touch_backtest(data, "BTC", "15m",
                                       exchange_now_ms=125*STEP)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["adverse_excursion_by_outcome"]["rebound"]["count"], 1)
        self.assertEqual(r["adverse_excursion_by_outcome"]["breakdown_on_touch"]["count"], 1)
        self.assertLess(
            r["adverse_excursion_by_outcome"]["rebound"]["mean_pre_outcome_mae_pct"],
            r["adverse_excursion_by_outcome"]["breakdown_on_touch"]["mean_pre_outcome_mae_pct"])

    def test_empty_categories_have_null_means(self):
        data = fixture()
        data[91]["high"], data[91]["close"] = 103, 102
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=mock_zones):
            r = support_touch_backtest(data, "ETH", "15m",
                                       exchange_now_ms=125*STEP, max_events=1)
        self.assertIsNone(
            r["adverse_excursion_by_outcome"]["breakdown"]["mean_pre_outcome_mae_pct"])
        self.assertEqual(sum(x["count"] for x in r["adverse_excursion_by_outcome"].values()),
                         len(r["events"]))

if __name__ == "__main__":
    unittest.main()
