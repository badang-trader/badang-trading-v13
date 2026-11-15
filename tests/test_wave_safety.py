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

    def test_oversized_structure_history_rejected(self):
        bars, reason = closed_bars(candles(5001), "15m")
        self.assertIsNone(bars)
        self.assertIn("상한", reason)

    def test_elliott_rules_reject_invalid_container_types(self):
        for invalid in (None, 123, "123456", {"a": 1}):
            with self.subTest(prices=invalid):
                result = completed_impulse_rules(invalid)
                self.assertFalse(result["valid"])

    def test_unknown_timeframe_rejected(self):
        bars, reason = closed_bars(candles(), 'unknown')
        self.assertIsNone(bars)
        self.assertIn('시간봉', reason)

    def test_contiguous_but_misaligned_candles_rejected(self):
        rows = candles()
        for row in rows:
            row[0] += 1
        bars, reason = closed_bars(rows, "15m")
        self.assertIsNone(bars)
        self.assertIn("경계 정렬", reason)

    def test_aligned_candles_still_accepted(self):
        bars, reason = closed_bars(candles(), "15m")
        self.assertEqual(reason, "OK")
        self.assertEqual(len(bars), 69)

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

    def test_disposable_future_slot_rejected_with_clock(self):
        rows = candles()
        # The preceding candle has closed, but a future-dated placeholder
        # must not be silently interpreted as the current slot.
        now_ms = rows[-2][0] + STEP
        rows[-1][0] += STEP
        bars, reason = closed_bars(rows, "15m", now_ms=now_ms)
        self.assertIsNone(bars)
        self.assertIn("미확정봉", reason)

    def test_disposable_current_slot_allowed_with_clock(self):
        rows = candles()
        now_ms = rows[-2][0] + STEP
        bars, reason = closed_bars(rows, "15m", now_ms=now_ms)
        self.assertEqual(reason, "OK")
        self.assertEqual(len(bars), 69)

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

    def test_invalid_pivot_confirmation_windows_rejected(self):
        bars, _ = closed_bars(candles(), "15m")
        for invalid in (0, -1, 1.5, None, True):
            with self.subTest(window=invalid):
                with self.assertRaisesRegex(ValueError, "window"):
                    confirmed_turns(bars, window=invalid)

    def test_disposable_last_row_timestamp_must_be_next_bar(self):
        for shift in (-STEP, 1, STEP):
            with self.subTest(shift=shift):
                rows = candles()
                rows[-1][0] += shift
                bars, reason = closed_bars(rows, "15m")
                self.assertIsNone(bars)
                self.assertIn("미확정봉", reason)

    def test_disposable_last_row_bad_prices_rejected(self):
        for column, value in ((1, "NaN"), (2, 90), (3, 110),
                              (4, 0), (5, -1), (5, "Infinity")):
            with self.subTest(column=column, value=value):
                rows = candles()
                rows[-1][column] = value
                bars, reason = closed_bars(rows, "15m")
                self.assertIsNone(bars)
                self.assertIn("미확정봉 OHLCV", reason)

    def test_disposable_last_row_structure_must_be_valid(self):
        for bad in (None, 42, [], ["NaN", 1, 2, 1, 2, 3]):
            with self.subTest(row=bad):
                rows = candles()
                rows[-1] = bad
                bars, reason = closed_bars(rows, "15m")
                self.assertIsNone(bars)
                self.assertIn("미확정봉", reason)

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

    def test_invalid_wave_volatility_and_current_price_fail_closed(self):
        turns = [{"price": 100, "time": 1}, {"price": 110, "time": 2},
                 {"price": 105, "time": 3}]
        for current, atr in ((float("nan"), 2), (115, 0),
                             (115, -1), (115, float("inf")),
                             ("bad", 2), (115, None)):
            with self.subTest(current=current, atr=atr):
                result = impulse_state(turns, current, atr)
                self.assertEqual(result["status"], "UNDETERMINED")
                self.assertEqual(result["alternatives"], [])

    def test_invalid_wave_pivot_payloads_fail_closed(self):
        valid = [{"price": 100, "time": 1}, {"price": 110, "time": 2},
                 {"price": 105, "time": 3}]
        for turns in (None, "bad", [None], [dict(valid[0], price="NaN")],
                      [dict(valid[0], time="bad")],
                      [dict(valid[0], time=-1)]):
            with self.subTest(turns=turns):
                result = impulse_state(turns, 115, 2)
                self.assertEqual(result["status"], "UNDETERMINED")

    def test_numeric_string_wave_pivots_normalized(self):
        turns = [{"price": "100", "time": "1"},
                 {"price": "110", "time": "2"},
                 {"price": "105", "time": "3"}]
        result = impulse_state(turns, 115, 2)
        self.assertEqual(result["status"], "HYPOTHESIS")
        self.assertEqual(result["alternatives"][0]["last_pivot_time"], 3)

    def test_reversed_or_duplicate_pivot_times_not_claimed_as_wave(self):
        for times in ((3, 2, 1), (1, 1, 3), (1, 3, 2)):
            with self.subTest(times=times):
                turns = [{"price": price, "time": time}
                         for price, time in zip((100, 110, 105), times)]
                result = impulse_state(turns, 115, 2)
                self.assertEqual(result["status"], "UNDETERMINED")

    def test_invalid_pivot_confirmation_times_not_claimed_as_wave(self):
        for bad in ("NaN", "bad", -1, 0, 1.5):
            with self.subTest(confirmed_at=bad):
                turns = [{"price": 100, "time": 1},
                         {"price": 110, "time": 2},
                         {"price": 105, "time": 3, "confirmed_at": bad}]
                result = impulse_state(turns, 115, 2)
                self.assertEqual(result["status"], "UNDETERMINED")

    def test_wave_pivot_confirmation_after_as_of_is_rejected(self):
        turns = [{"price": 100, "time": 1, "confirmed_at": 4},
                 {"price": 110, "time": 2, "confirmed_at": 5},
                 {"price": 105, "time": 3, "confirmed_at": 6}]
        result = impulse_state(turns, 115, 2, as_of_open=5)
        self.assertEqual(result["status"], "UNDETERMINED")
        self.assertEqual(result["alternatives"], [])

    def test_wave_pivot_confirmation_at_as_of_is_allowed(self):
        turns = [{"price": 100, "time": 1, "confirmed_at": 4},
                 {"price": 110, "time": 2, "confirmed_at": 5},
                 {"price": 105, "time": 3, "confirmed_at": 6}]
        result = impulse_state(turns, 115, 2, as_of_open=6)
        self.assertEqual(result["status"], "HYPOTHESIS")

    def test_wave_pivot_after_as_of_is_rejected(self):
        turns = [{"price": 100, "time": 1}, {"price": 110, "time": 2},
                 {"price": 105, "time": 3}]
        result = impulse_state(turns, 115, 2, as_of_open=2)
        self.assertEqual(result["status"], "UNDETERMINED")

    def test_elliott_pivot_kinds_must_alternate(self):
        for kinds in (("L", "L", "L"), ("L", "H", "H"),
                      ("L", "X", "L"), ("L", None, "L")):
            with self.subTest(kinds=kinds):
                turns=[{"price":p, "time":i+1, "kind":k}
                       for i,(p,k) in enumerate(zip((100,110,105),kinds))]
                self.assertEqual(impulse_state(turns,115,2)["status"],
                                 "UNDETERMINED")

    def test_elliott_pivot_kind_must_match_price_direction(self):
        turns=[{"price":100,"time":1,"kind":"H"},
               {"price":110,"time":2,"kind":"L"},
               {"price":105,"time":3,"kind":"H"}]
        self.assertEqual(impulse_state(turns,115,2)["status"],
                         "UNDETERMINED")

    def test_numeric_string_pivots_with_valid_kinds_still_work(self):
        turns=[{"price":"100","time":1,"kind":"L"},
               {"price":"110","time":2,"kind":"H"},
               {"price":"105","time":3,"kind":"L"}]
        self.assertEqual(impulse_state(turns,115,2)["status"],"HYPOTHESIS")

    def test_as_of_requires_explicit_pivot_confirmation(self):
        turns=[{"price":100,"time":1,"confirmed_at":4},
               {"price":110,"time":2,"confirmed_at":5},
               {"price":105,"time":3}]
        result=impulse_state(turns,115,2,as_of_open=6)
        self.assertEqual(result["status"],"UNDETERMINED")
        self.assertEqual(result["alternatives"],[])

    def test_legacy_wave_without_as_of_does_not_invent_confirmation(self):
        turns=[{"price":100,"time":1},{"price":110,"time":2},
               {"price":105,"time":3}]
        result=impulse_state(turns,115,2)
        self.assertEqual(result["status"],"HYPOTHESIS")
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

    def test_declared_costs_must_match_both_net_targets(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        base = {"side": "LONG", "score": 95, "entry": 100, "stop": 98,
                "tp1": 104, "tp2": 106, "state": "READY_REVIEW",
                "fee_assumption_roundtrip_pct": 0.12,
                "slippage_assumption_roundtrip_pct": 0.10,
                "rr1_net_estimate": 1.76, "rr2_net_estimate": 2.86}
        result = decision_review({"decision_plan_425": base}, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        correct = dict(base, rr1_net_estimate=1.70, rr2_net_estimate=2.60)
        # 3.78 / 2.22 = 1.70; 5.78 / 2.22 = 2.60
        result = decision_review({"decision_plan_425": correct}, structures, "scalp")
        self.assertEqual(result["state"], "READY_REVIEW")
        bad = dict(correct, rr2_net_estimate=2.85)
        result = decision_review({"decision_plan_425": bad}, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("2차 순손익비" in reason for reason in result["reasons"]))

    def test_scanner_cannot_omit_all_cost_assumptions(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"recommendation": "LONG", "decision_plan_425": {
            "side": "LONG", "score": 95, "entry": 100, "stop": 98,
            "tp1": 104, "tp2": 106, "state": "READY_REVIEW",
            "rr1_net_estimate": 1.70, "rr2_net_estimate": 2.60}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("스캔 비용 가정 누락" in reason
                            for reason in result["reasons"]))

    def test_declared_costs_require_second_target_price(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {
            "side": "LONG", "score": 95, "entry": 100, "stop": 98,
            "tp1": 104, "state": "READY_REVIEW",
            "fee_assumption_roundtrip_pct": 0.12,
            "slippage_assumption_roundtrip_pct": 0.10,
            "rr1_net_estimate": 1.70}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("2차 목표 가격 누락" in reason
                            for reason in result["reasons"]))

    def test_declared_second_target_requires_net_ratio(self):
        structures = {tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        item = {"decision_plan_425": {
            "side": "LONG", "score": 95, "entry": 100, "stop": 98,
            "tp1": 104, "tp2": 106, "state": "READY_REVIEW",
            "fee_assumption_roundtrip_pct": 0.12,
            "slippage_assumption_roundtrip_pct": 0.10,
            "rr1_net_estimate": 1.70}}
        result = decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("2차 순손익비 누락" in reason
                            for reason in result["reasons"]))

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

    def test_scanner_wait_cannot_be_resurrected_by_decision_plan(self):
        item={"recommendation": "WAIT",
              "decision_plan_425": {"side": "LONG", "score": 95,
                  "entry": 100, "stop": 98, "tp1": 104,
                  "rr1_net_estimate": 1.8, "state": "READY_REVIEW"}}
        structures={tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        result=decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("스캔 최종 추천" in r for r in result["reasons"]))

    def test_entry_blockers_override_stale_ready_plan(self):
        item={"recommendation": "LONG", "entry_blockers": ["확정봉 누락"],
              "decision_plan_425": {"side": "LONG", "score": 95,
                  "entry": 100, "stop": 98, "tp1": 104,
                  "rr1_net_estimate": 1.8, "state": "READY_REVIEW"}}
        structures={tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        result=decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "WAIT")
        self.assertTrue(any("차단 사유" in r for r in result["reasons"]))

    def test_malformed_decision_payload_cannot_be_ready(self):
        for item in (None, [], {"decision_plan_425": "bad"},
                     {"decision_plan_425": {"reasons": {"bad": "shape"}}}):
            with self.subTest(item=item):
                result=decision_review(item, {}, "scalp")
                self.assertEqual(result["state"], "WAIT")

    def test_malformed_structure_payload_cannot_be_ready(self):
        item={"decision_plan_425": {"side": "LONG", "score": 95,
             "rr1_net_estimate": 1.8, "entry": 100, "stop": 95,
             "tp1": 110, "state": "READY_REVIEW"}}
        for structures in (None, [], {"15m": "bad", "30m": None, "1H": []}):
            with self.subTest(structures=structures):
                result=decision_review(item, structures, "scalp")
                self.assertEqual(result["state"], "WAIT")

    def test_malformed_wave_label_cannot_crash_ready_review(self):
        item={"decision_plan_425": {"side": "LONG", "score": 95,
             "rr1_net_estimate": 1.8, "entry": 100, "stop": 95,
             "tp1": 110, "state": "READY_REVIEW"}}
        structures={tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        structures["15m"]["wave"] = ["malformed"]
        result=decision_review(item, structures, "scalp")
        self.assertEqual(result["wave_context"], "파동 분석 불가")

    def test_wave_alternatives_include_invalidation_levels(self):
        item={"decision_plan_425": {"side": "LONG", "score": 95,
              "rr1_net_estimate": 1.8, "entry": 100, "stop": 95,
              "tp1": 110, "state": "READY_REVIEW"}}
        structures={tf: {"status": "OK"} for tf in ("15m", "30m", "1H")}
        structures["15m"]["wave"]={"label": "3파·5파 복수 시나리오",
            "alternatives": [
                {"wave": 3, "direction": "UP", "invalidation": 94.5,
                 "last_pivot_confirmed_at": 900000},
                {"wave": 5, "direction": "UP", "invalidation": 96.0,
                 "last_pivot_confirmed_at": 1800000}]}
        result=decision_review(item, structures, "scalp")
        self.assertEqual(result["state"], "READY_REVIEW")
        self.assertEqual(len(result["wave_scenarios"]), 2)
        self.assertEqual(result["wave_scenarios"][0]["invalidation"], 94.5)
        self.assertEqual(result["wave_scenarios"][1]["wave"], 5)

    def test_invalid_wave_alternatives_not_exposed(self):
        item={"decision_plan_425": {}}
        structures={"4H": {"status": "OK", "wave": {"alternatives": [
            None, "bad", {"wave": 3, "direction": "UP", "invalidation": "NaN"},
            {"wave": 5, "direction": "SIDEWAYS", "invalidation": 99},
            {"wave": 3, "direction": "DOWN", "invalidation": 98}]}}}
        result=decision_review(item, structures, "swing")
        self.assertEqual(len(result["wave_scenarios"]), 1)
        self.assertEqual(result["wave_scenarios"][0]["direction"], "DOWN")
        self.assertEqual(result["state"], "WAIT")

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
