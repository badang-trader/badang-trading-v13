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

    def test_invalid_top_level_candle_payload_fails_safely(self):
        for bad in (None, 123, "not-candles", {"data": candles()}):
            with self.subTest(payload_type=type(bad).__name__):
                bars, reason = closed_bars(bad, "15m")
                self.assertIsNone(bars)
                self.assertIn("형식", reason)

    def test_malformed_candle_rows_fail_without_crashing(self):
        for bad in (None, 7, "bad", {"timestamp": 1}, []):
            with self.subTest(row=bad):
                rows = candles()
                rows[20] = bad
                bars, reason = closed_bars(rows, "15m")
                self.assertIsNone(bars)
                self.assertIn("형식", reason)

    def test_fractional_and_invalid_timestamps_rejected(self):
        for bad in (30 * STEP + 0.5, -1, "NaN", "Infinity"):
            with self.subTest(timestamp=bad):
                rows = candles()
                rows[29][0] = bad
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

    def test_wave_hypothesis_exposes_pivot_confirmation(self):
        turns = [
            {"price": 100, "time": 1, "confirmed_at": 4},
            {"price": 110, "time": 2, "confirmed_at": 5},
            {"price": 105, "time": 3, "confirmed_at": 6},
        ]
        result = impulse_state(turns, 115, 2)
        self.assertEqual(result["status"], "HYPOTHESIS")
        self.assertEqual(result["alternatives"][0]["last_pivot_confirmed_at"], 6)
        self.assertGreater(result["alternatives"][0]["last_pivot_confirmed_at"],
                           result["alternatives"][0]["last_pivot_time"])

    def test_wave_confirmation_missing_is_not_fabricated(self):
        turns = [{"price": 100, "time": 1},
                 {"price": 110, "time": 2},
                 {"price": 105, "time": 3}]
        result = impulse_state(turns, 115, 2)
        self.assertIsNone(result["alternatives"][0]["last_pivot_confirmed_at"])

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

    def test_malformed_reward_risk_fails_safely(self):
        valid_structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        for bad in ("not-a-number", None, float("nan"), float("inf"), -2):
            with self.subTest(rr=bad):
                item = {"decision_plan_425": {"side": "LONG", "score": 90,
                        "rr1_net_estimate": bad, "state": "READY_REVIEW"}}
                result = decision_review(item, valid_structures, "scalp")
                self.assertEqual(result["state"], "WAIT")
                self.assertTrue(any("손익비" in r for r in result["reasons"]))

    def test_numeric_string_reward_risk_is_normalized(self):
        valid_structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {"side": "LONG", "score": "90",
                "entry": "100", "stop": "98", "tp1": "104",
                "rr1_net_estimate": "1.7", "rr2_net_estimate": "2.2",
                "state": "READY_REVIEW"}}
        result = decision_review(item, valid_structures, "scalp")
        self.assertEqual(result["state"], "READY_REVIEW")
        self.assertEqual(result["plan"]["rr1_net_estimate"], 1.7)

    def test_missing_trade_prices_cannot_be_ready(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {"side": "LONG", "score": 95,
                "rr1_net_estimate": 2, "state": "READY_REVIEW"}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("가격" in reason for reason in result["reasons"]))

    def test_inverted_long_and_short_prices_rejected(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        for side, stop, tp1 in (("LONG", 102, 104), ("SHORT", 98, 96),
                                ("LONG", 98, 96), ("SHORT", 102, 104)):
            with self.subTest(side=side, stop=stop, tp1=tp1):
                item = {"decision_plan_425": {"side": side, "score": 95,
                        "entry": 100, "stop": stop, "tp1": tp1,
                        "rr1_net_estimate": 2, "state": "READY_REVIEW"}}
                result = decision_review(item, structures, "scalp")
                self.assertEqual(result["state"], "WAIT")

    def test_valid_short_price_geometry(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {"side": "SHORT", "score": 95,
                "entry": 100, "stop": 102, "tp1": 96,
                "rr1_net_estimate": 2, "state": "READY_REVIEW"}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "READY_REVIEW")

    def test_net_reward_risk_cannot_exceed_gross_price_ratio(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        for side, stop, tp1 in (("LONG", 98, 104), ("SHORT", 102, 96)):
            with self.subTest(side=side):
                item = {"decision_plan_425": {"side": side, "score": 95,
                        "entry": 100, "stop": stop, "tp1": tp1,
                        "rr1_net_estimate": 2.5, "state": "READY_REVIEW"}}
                result = decision_review(item, structures, "scalp")
                self.assertEqual(result["state"], "WAIT")
                self.assertTrue(any("손익비" in r for r in result["reasons"]))

    def test_net_reward_risk_below_gross_remains_eligible(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {"side": "LONG", "score": 95,
                "entry": 100, "stop": 98, "tp1": 104,
                "rr1_net_estimate": 1.8, "state": "READY_REVIEW"}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "READY_REVIEW")

    def test_second_target_must_not_be_worse_than_first(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        for side, stop, tp1, tp2 in (("LONG", 98, 104, 103),
                                     ("SHORT", 102, 96, 97)):
            with self.subTest(side=side):
                item = {"decision_plan_425": {"side": side, "score": 95,
                        "entry": 100, "stop": stop, "tp1": tp1, "tp2": tp2,
                        "rr1_net_estimate": 1.8, "state": "READY_REVIEW"}}
                result = decision_review(item, structures, "scalp")
                self.assertEqual(result["state"], "WAIT")
                self.assertTrue(any("2차 목표가" in r for r in result["reasons"]))

    def test_second_target_net_ratio_cannot_exceed_gross(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {"side": "LONG", "score": 95,
                "entry": 100, "stop": 98, "tp1": 104, "tp2": 106,
                "rr1_net_estimate": 1.8, "rr2_net_estimate": 4,
                "state": "READY_REVIEW"}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("2차 수수료" in r for r in result["reasons"]))

    def test_valid_second_target_remains_eligible(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {"side": "SHORT", "score": 95,
                "entry": 100, "stop": 102, "tp1": 96, "tp2": 94,
                "rr1_net_estimate": 1.8, "rr2_net_estimate": 2.8,
                "state": "READY_REVIEW"}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "READY_REVIEW")

    def test_unknown_analysis_mode_never_returns_ready(self):
        item = {"decision_plan_425": {"side": "LONG", "score": 95,
                "rr1_net_estimate": 3.0, "state": "READY_REVIEW"}}
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H", "4H", "1D")}
        for mode in ("", "SCALP", "unknown", None):
            with self.subTest(mode=mode):
                result = decision_review(item, structures, mode)
                self.assertEqual(result["state"], "WAIT")
                self.assertIn("지원하지 않는 분석 모드", result["reasons"])

    def test_missing_timeframe_prevents_ready_state(self):
        item = {"decision_plan_425": {"side": "LONG", "score": 90,
                "rr1_net_estimate": 2.0, "state": "READY_REVIEW"}}
        result = decision_review(item, {}, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(result["reasons"])

if __name__ == "__main__":
    unittest.main()
