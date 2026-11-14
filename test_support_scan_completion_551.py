"""Verify scan completeness flags with real loop execution, not mocked backtest."""
import unittest
from unittest.mock import patch
from badang_support_backtest_545 import support_touch_backtest

STEP = 900000

def bars(n=105):
    return [{"timestamp": i*STEP, "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 10} for i in range(n)]

def zones(*args, **kwargs):
    return {"status": "ok", "zones": [{"status": "historical_support",
            "lower": 99, "upper": 100.5, "center": 100,
            "evidence_score": 70}]}

class ScanCompletionTests(unittest.TestCase):
    def test_invalid_direct_backtest_parameters(self):
        cases = [
            {"horizon": True}, {"horizon": 1.5},
            {"warmup": False}, {"warmup": 60.5},
            {"max_events": True}, {"max_events": 0},
            {"rebound_pct": True}, {"rebound_pct": float("nan")},
            {"rebound_pct": float("inf")}, {"rebound_pct": 10**1000}, {"rebound_pct": "0.5"},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    support_touch_backtest(
                        bars(), "BTC", "15m", exchange_now_ms=105*STEP,
                        **overrides)

    def test_early_event_cap_marks_incomplete(self):
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=zones):
            r = support_touch_backtest(
                bars(), "BTC", "15m", max_events=1,
                exchange_now_ms=105*STEP)
        self.assertEqual(len(r["events"]), 1)
        self.assertFalse(r["scan_complete"])
        self.assertTrue(r["event_cap_reached"])

    def test_exactly_one_event_with_completed_scan_not_truncated(self):
        # 99 candles: with horizon 8 and warmup 90, only index 90
        # can be evaluated. The one-event cap is not a truncation.
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=zones):
            r = support_touch_backtest(
                bars(99), "ETH", "15m", max_events=1,
                exchange_now_ms=99*STEP)
        self.assertEqual(len(r["events"]), 1)
        self.assertTrue(r["scan_complete"])
        self.assertFalse(r["event_cap_reached"])

    def test_no_events_also_completes_scan(self):
        def no_zones(*args, **kwargs):
            return {"status": "ok", "zones": []}
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=no_zones):
            r = support_touch_backtest(
                bars(), "BTC", "15m", max_events=1,
                exchange_now_ms=105*STEP)
        self.assertEqual(r["events"], [])
        self.assertTrue(r["scan_complete"])
        self.assertFalse(r["event_cap_reached"])

if __name__ == "__main__":
    unittest.main()
