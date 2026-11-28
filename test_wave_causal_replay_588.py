import unittest
from unittest.mock import patch
from badang_wave_causal_replay_588 import replay_wave_scenarios

def candles(n=32):
    return [{"open": 100., "high": 101., "low": 99.,
             "close": 100., "volume": 10.} for _ in range(n)]

class WaveCausalReplayTests(unittest.TestCase):
    def test_only_closed_prefixes_are_passed(self):
        observed = []
        def engine(prefix):
            observed.append(len(prefix))
            return {"status": "no_valid_candidate", "scenarios": []}
        with patch("badang_wave_causal_replay_588.wave_choice_response",
                   side_effect=engine):
            report = replay_wave_scenarios(candles(), warmup=25, stride=2)
        self.assertEqual(observed, [25, 27, 29, 31])
        self.assertEqual(report["observations"][-1]["asof_closed_bar_index"], 30)
        self.assertFalse(report["trading_ready"])

    def test_future_changes_cannot_affect_earlier_observation(self):
        rows = candles()
        before = replay_wave_scenarios(rows, warmup=25)
        rows[-1]["close"] = 99.
        after = replay_wave_scenarios(rows, warmup=25)
        self.assertEqual(before["observations"][:-1], after["observations"][:-1])

    def test_invalid_data_fails_closed(self):
        rows = candles()
        rows[5]["low"] = 102.
        with self.assertRaisesRegex(ValueError, "Invalid historical"):
            replay_wave_scenarios(rows, warmup=25)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            replay_wave_scenarios(candles(), warmup=24)
        with self.assertRaises(ValueError):
            replay_wave_scenarios(candles(), warmup=25, stride=0)

if __name__ == "__main__":
    unittest.main()
