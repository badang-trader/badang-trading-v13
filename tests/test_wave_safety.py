"""Regression checks for closed-candle and Elliott hypothesis handling.

No network access, database, or live orders required.
"""
import unittest
from badang_decision_427 import closed_bars, confirmed_turns, impulse_state, decision_review, completed_impulse_rules

STEP = 900_000

def candles(n=70):
    return [[(i+1)*STEP, 100.0, 102.0, 98.0, 100.0, 10.0] for i in range(n)]

class WaveSafetyTests(unittest.TestCase):
    def test_incomplete_last_candle_excluded(self):
        bars, reason = closed_bars(candles(), "15m")
        self.assertEqual(reason, "OK")
        self.assertEqual(len(bars), 69)

    def test_unknown_timeframe_rejected(self):
        bars, reason = closed_bars(candles(), 'unknown')
        self.assertIsNone(bars)
        self.assertIn('시간봉', reason)

    def test_duplicate_timestamp_rejected(self):
        rows = candles()
        rows[30][0] = rows[29][0]
        bars, reason = closed_bars(rows, '15m')
        self.assertIsNone(bars)
        self.assertIn('간격', reason)

    def test_gap_rejected(self):
        rows = candles()
        rows[35][0] += 1
        bars, reason = closed_bars(rows, "15m")
        self.assertIsNone(bars)
        self.assertIn("간격", reason)

    def test_invalid_ohlcv_rejected(self):
        rows = candles()
        rows[20][2] = 90
        bars, reason = closed_bars(rows, "15m")
        self.assertIsNone(bars)
        self.assertIn("이상", reason)

    def test_future_last_closed_rejected(self):
        rows = candles()
        bars, reason = closed_bars(rows, "15m", now_ms=rows[-3][0])
        self.assertIsNone(bars)
        self.assertIn("확정되지", reason)

    def test_bar_open_is_not_a_confirmed_close(self):
        rows = candles()
        last_used_open = rows[-2][0]
        bars, reason = closed_bars(rows, "15m", now_ms=last_used_open + STEP - 1)
        self.assertIsNone(bars)
        self.assertIn("확정되지", reason)

    def test_bar_close_boundary_is_accepted(self):
        rows = candles()
        last_used_open = rows[-2][0]
        bars, reason = closed_bars(rows, "15m", now_ms=last_used_open + STEP)
        self.assertEqual(reason, "OK")
        self.assertEqual(len(bars), 69)

    def test_stale_candle_is_rejected(self):
        rows = candles()
        last_used_open = rows[-2][0]
        bars, reason = closed_bars(rows, "15m", now_ms=last_used_open + STEP * 5)
        self.assertIsNone(bars)
        self.assertIn("오래됨", reason)

    def test_pivots_require_right_hand_confirmation(self):
        rows = candles()
        bars, _ = closed_bars(rows, "15m")
        turns = confirmed_turns(bars, window=3)
        self.assertTrue(all(t["i"] < len(bars)-3 for t in turns))

    def test_pivot_confirmation_is_later_than_pivot(self):
        rows = candles()
        rows[30][2] = 110.0
        bars, _ = closed_bars(rows, "15m")
        turns = confirmed_turns(bars, window=3)
        high = next(t for t in turns if t["kind"] == "H" and t["i"] == 30)
        self.assertEqual(high["confirmed_at"], bars[33][0])
        self.assertGreater(high["confirmed_at"], high["time"])

    def test_pivot_not_visible_before_right_hand_bars(self):
        rows = candles()
        rows[30][2] = 110.0
        full_bars, _ = closed_bars(rows, "15m")
        early = confirmed_turns(full_bars[:33], window=3)
        later = confirmed_turns(full_bars[:34], window=3)
        self.assertFalse(any(t["i"] == 30 for t in early))
        self.assertTrue(any(t["i"] == 30 for t in later))

    def test_insufficient_pivots_not_claimed_as_wave(self):
        wave = impulse_state([], 100, 1)
        self.assertEqual(wave["status"], "UNDETERMINED")

    def test_completed_impulse_valid(self):
        result = completed_impulse_rules([100, 110, 105, 125, 118, 132])
        self.assertTrue(result["valid"], result["reasons"])

    def test_wave_three_cannot_be_shortest(self):
        result = completed_impulse_rules([100, 120, 110, 125, 121, 150])
        self.assertFalse(result["valid"])
        self.assertTrue(any("최단" in r for r in result["reasons"]))

    def test_wave_two_cannot_cross_origin(self):
        result = completed_impulse_rules([100, 110, 99, 130, 120, 140])
        self.assertFalse(result["valid"])
        self.assertTrue(any("출발점" in r for r in result["reasons"]))

    def test_wave_four_overlap_rejected(self):
        result = completed_impulse_rules([100, 120, 110, 140, 118, 155])
        self.assertFalse(result["valid"])
        self.assertTrue(any("중첩" in r for r in result["reasons"]))

    def test_wave_three_shortest_bearish(self):
        result = completed_impulse_rules([150, 130, 140, 125, 129, 100])
        self.assertFalse(result["valid"])
        self.assertTrue(any("최단" in r for r in result["reasons"]))

    def test_missing_timeframe_prevents_ready_state(self):
        item = {"decision_plan_425": {"side": "LONG", "score": 90,
                "rr1_net_estimate": 2.0, "state": "READY_REVIEW"}}
        result = decision_review(item, {}, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(result["reasons"])

if __name__ == "__main__":
    unittest.main()
