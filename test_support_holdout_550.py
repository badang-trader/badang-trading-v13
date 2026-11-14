"""Holdout split must exclude events spanning the boundary."""
import unittest
from unittest.mock import patch
from badang_support_holdout_550 import chronological_support_holdout

STEP = 900000

def bars(n=200):
    return [{"timestamp": i*STEP, "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 10} for i in range(n)]

def event(i, outcome="rebound"):
    return {"touch_bar_index": i, "outcome": outcome,
            "pre_outcome_max_adverse_excursion_pct": 2.0}

class HoldoutTests(unittest.TestCase):
    def test_split_boundary_is_excluded(self):
        # Split at 140. Horizon 8: event 135 crosses into holdout.
        events = [event(100), event(135), event(140),
                  event(150, "breakdown")]
        with patch("badang_support_holdout_550.support_touch_backtest",
                   return_value={"status": "ok", "events": events}):
            r = chronological_support_holdout(
                bars(), "BTC", "15m", exchange_now_ms=200*STEP,
                min_resolved=1)
        self.assertEqual(r["split_index"], 140)
        self.assertEqual(r["train"]["event_count"], 1)
        self.assertEqual(r["holdout"]["event_count"], 2)
        self.assertEqual(r["holdout"]["rebound_fraction"], 0.5)

    def test_low_sample_hides_fraction(self):
        with patch("badang_support_holdout_550.support_touch_backtest",
                   return_value={"status": "ok", "events": [event(150)]}):
            r = chronological_support_holdout(
                bars(), "ETH", "15m", exchange_now_ms=200*STEP)
        self.assertIsNone(r["holdout"]["rebound_fraction"])
        self.assertFalse(r["holdout"]["adequate_sample"])

    def test_invalid_split(self):
        with self.assertRaises(ValueError):
            chronological_support_holdout(
                bars(), "BTC", "15m", exchange_now_ms=200*STEP,
                train_fraction=0.99)

if __name__ == "__main__":
    unittest.main()
