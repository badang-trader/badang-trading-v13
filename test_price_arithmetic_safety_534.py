"""Extreme but finite price levels cannot produce nonfinite scenarios or candidates."""
import unittest
from app import scenario,recommend_candidates

class PriceArithmeticSafetyTests(unittest.TestCase):
    def test_scenario_overflow_rejected(self):
        setup={"price":1e308,"atr":1e308,"swing_low":1e307,"swing_high":1e308}
        self.assertIsNone(scenario(setup,"LONG","scalp"))
        self.assertIsNone(scenario(setup,"SHORT","scalp"))
    def test_candidate_infinite_reward_rejected(self):
        item={"signal":"LONG","long_score":95,
              "plan":{"entry":1e-308,"stop":5e-309,"tp1":1e308}}
        self.assertEqual(recommend_candidates([item]),[])
    def test_normal_scenario_retained(self):
        setup={"price":100,"atr":2,"swing_low":95,"swing_high":105}
        result=scenario(setup,"LONG","scalp")
        self.assertIsNotNone(result)
        self.assertLess(result["stop"],result["entry"])
        self.assertLess(result["entry"],result["tp1"])
    def test_normal_candidate_retained(self):
        item={"signal":"LONG","long_score":90,
              "plan":{"entry":100,"stop":95,"tp1":110}}
        self.assertEqual(len(recommend_candidates([item])),1)

if __name__=="__main__":unittest.main()
