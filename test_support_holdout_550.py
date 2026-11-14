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
        self.assertTrue(r["holdout_sample_adequate"])
        self.assertEqual(r["holdout_event_coverage"]["first_touch_index"], 140)
        self.assertEqual(r["holdout_event_coverage"]["last_touch_index"], 150)

    def test_low_sample_hides_fraction(self):
        with patch("badang_support_holdout_550.support_touch_backtest",
                   return_value={"status": "ok", "events": [event(150)]}):
            r = chronological_support_holdout(
                bars(), "ETH", "15m", exchange_now_ms=200*STEP)
        self.assertIsNone(r["holdout"]["rebound_fraction"])
        self.assertFalse(r["holdout"]["adequate_sample"])
        self.assertFalse(r["holdout_sample_adequate"])

    def test_event_cap_refuses_biased_holdout(self):
        events = [event(100)] * 1000
        with patch("badang_support_holdout_550.support_touch_backtest",
                   return_value={"status": "ok", "events": events}):
            r = chronological_support_holdout(
                bars(), "BTC", "15m", exchange_now_ms=200*STEP)
        self.assertEqual(r["status"], "event_cap_reached")
        self.assertFalse(r["trading_ready"])
        self.assertNotIn("holdout", r)

    def test_exactly_cap_events_with_complete_scan_are_allowed(self):
        events = [event(100)] * 1000
        with patch("badang_support_holdout_550.support_touch_backtest",
                   return_value={"status": "ok", "events": events,
                                 "scan_complete": True,
                                 "event_cap_reached": False}):
            r = chronological_support_holdout(
                bars(), "BTC", "15m", exchange_now_ms=200*STEP)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["train"]["event_count"], 1000)

    def test_explicit_cap_flag_rejects_even_under_1000_events(self):
        with patch("badang_support_holdout_550.support_touch_backtest",
                   return_value={"status": "ok", "events": [event(100)],
                                 "scan_complete": False,
                                 "event_cap_reached": True}):
            r = chronological_support_holdout(
                bars(), "ETH", "15m", exchange_now_ms=200*STEP)
        self.assertEqual(r["status"], "event_cap_reached")

    def test_nonfinite_and_boolean_inputs_rejected(self):
        for invalid in (float("nan"), float("inf"), -float("inf"), True, False, "0.7"):
            with self.subTest(train_fraction=repr(invalid)):
                with self.assertRaises(ValueError):
                    chronological_support_holdout(
                        bars(), "BTC", "15m", exchange_now_ms=200*STEP,
                        train_fraction=invalid)
        for invalid in (True, False, 0):
            with self.subTest(min_resolved=repr(invalid)):
                with self.assertRaises(ValueError):
                    chronological_support_holdout(
                        bars(), "BTC", "15m", exchange_now_ms=200*STEP,
                        min_resolved=invalid)

    def test_invalid_horizon_warmup_and_rebound_rejected(self):
        cases = [
            {"horizon": True}, {"horizon": 1.5}, {"horizon": 0},
            {"warmup": True}, {"warmup": 60.5}, {"warmup": 59},
            {"rebound_pct": True}, {"rebound_pct": float("nan")},
            {"rebound_pct": float("inf")}, {"rebound_pct": 0},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    chronological_support_holdout(
                        bars(), "BTC", "15m", exchange_now_ms=200*STEP,
                        **overrides)

    def test_invalid_split(self):
        with self.assertRaises(ValueError):
            chronological_support_holdout(
                bars(), "BTC", "15m", exchange_now_ms=200*STEP,
                train_fraction=0.99)

if __name__ == "__main__":
    unittest.main()
