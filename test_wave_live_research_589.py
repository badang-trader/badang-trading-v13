import unittest
from unittest.mock import patch
from badang_wave_live_research_589 import evaluate_wave_target

class WaveLiveResearchTests(unittest.TestCase):
    def test_insufficient_history_never_replays(self):
        with patch("badang_wave_live_research_589.research_history",
                   return_value={"status": "insufficient_history",
                                 "stop_reason": "historical_gap"}):
            def fail(*args, **kwargs):
                raise AssertionError("Replay must not run")
            result = evaluate_wave_target("BTCUSDT", "15m", replay=fail)
        self.assertEqual(result["status"], "insufficient_history")
        self.assertFalse(result["trading_ready"])

    def test_repeated_observations_are_not_claimed_as_trades(self):
        with patch("badang_wave_live_research_589.research_history",
                   return_value={"status": "ok", "candles": [
                       [str(1800000000000 + i * 900000),
                        "100", "101", "99", "100", "1"]
                       for i in range(1000)]}):
            def fake_replay(rows, *, warmup, stride):
                self.assertEqual((len(rows), warmup, stride), (1000, 205, 5))
                return {"observations": [
                    {"candidate_count": 1, "scenarios": [{
                        "direction": "down", "pattern": "impulse",
                        "invalidation_status": "not_crossed"}]},
                    {"candidate_count": 1, "scenarios": [{
                        "direction": "down", "pattern": "impulse",
                        "invalidation_status": "crossed_or_at_level"}]},
                ]}
            result = evaluate_wave_target("BTCUSDT", "15m",
                                          replay=fake_replay)
        self.assertEqual(result["candidate_observation_counts_by_direction"]["down"], 2)
        self.assertEqual(result["already_crossed_invalidation_observations"], 1)
        self.assertTrue(result["counts_are_repeated_observations_not_independent_trades"])
        self.assertFalse(result["prediction_accuracy_verified"])

if __name__ == "__main__":
    unittest.main()
