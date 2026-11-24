import unittest
from unittest.mock import patch
from badang_wave_choice_response_587 import wave_choice_response

def bars(n=40):
    return [{"open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 10.0} for _ in range(n)]

class WaveChoiceResponseTests(unittest.TestCase):
    def test_no_forced_signal_without_candidates(self):
        with patch("badang_wave_choice_response_587.wave_candidates", return_value=[]):
            result = wave_choice_response(bars())
        self.assertEqual(result["status"], "no_valid_candidate")
        self.assertFalse(result["trading_ready"])
        self.assertFalse(result["automatic_orders"])

    def test_alternatives_and_invalidation_are_preserved(self):
        alternatives = [
            {"pattern": "ABC", "direction": "up", "confidence": "low",
             "invalidation_price": 95.0},
            {"pattern": "impulse", "direction": "down", "confidence": "medium",
             "invalidation_price": 105.0},
        ]
        with patch("badang_wave_choice_response_587.wave_candidates",
                   return_value=alternatives):
            result = wave_choice_response(bars())
        self.assertEqual(len(result["scenarios"]), 2)
        self.assertTrue(all(x["invalidation_status"] == "not_evaluated"
                            for x in result["scenarios"]))
        self.assertTrue(all("do_not_auto_reverse" in x["response_if_invalidated"]
                            for x in result["scenarios"]))

    def test_crossing_reference_is_not_called_wave_invalidation(self):
        candidate = [{"pattern": "ABC", "direction": "up",
                      "invalidation_price": 105.0}]
        with patch("badang_wave_choice_response_587.wave_candidates",
                   return_value=candidate):
            scenario = wave_choice_response(bars())["scenarios"][0]
        self.assertEqual(scenario["invalidation_status"], "not_evaluated")
        self.assertFalse(scenario["invalidation_rule_verified"])

    def test_unconfirmed_pivot_is_not_a_current_candidate(self):
        candidate = {"pattern": "ABC", "direction": "up",
                     "invalidation_price": 95.0,
                     "first_observable_bar_index": 42,
                     "observable_in_snapshot": False}
        with patch("badang_wave_choice_response_587.wave_candidates",
                   return_value=[candidate]) as engine:
            result = wave_choice_response(bars(40))
        engine.assert_called_once()
        self.assertEqual(engine.call_args.kwargs["total_bars"], 40)
        self.assertEqual(result["scenarios"], [])
        self.assertFalse(result["trading_ready"])

    def test_confirmed_pivot_timing_is_visible(self):
        candidate = {"pattern": "ABC", "direction": "down",
                     "invalidation_price": 105.0,
                     "first_observable_bar_index": 38,
                     "pivot_confirmation_bars": 3,
                     "observable_in_snapshot": True}
        with patch("badang_wave_choice_response_587.wave_candidates",
                   return_value=[candidate]):
            result = wave_choice_response(bars(40))
        self.assertEqual(result["scenarios"][0]["first_observable_bar_index"], 38)
        self.assertTrue(result["scenarios"][0]["pivot_timing_verified"])

    def test_invalid_candle_is_not_silently_dropped(self):
        rows = bars()
        rows[15]["high"] = 1.0
        self.assertEqual(wave_choice_response(rows)["status"], "invalid_data")

    def test_insufficient_data_does_not_create_signal(self):
        self.assertEqual(wave_choice_response(bars(12))["status"], "insufficient_data")

if __name__ == "__main__":
    unittest.main()
