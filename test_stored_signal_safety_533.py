"""Persist only finite risk/reward and correctly ordered second targets."""
import unittest
from app import extract_v13_signal

def signal(**kwargs):
    item={"symbol":"BTCUSDT","recommendation":"LONG","long_score":90,
          "entry_reference":100,"stop_loss":95,"take_profit_1":110,
          "take_profit_2":120,"timestamp":1700000000000}
    item.update(kwargs)
    return extract_v13_signal(item,"scalp")

class StoredSignalSafetyTests(unittest.TestCase):
    def test_valid_long_second_target(self):
        self.assertEqual(signal()["tp2_price"],120)
    def test_long_second_target_behind_first_is_omitted(self):
        self.assertIsNone(signal(take_profit_2=105)["tp2_price"])
    def test_short_second_target_behind_first_is_omitted(self):
        item={"symbol":"BTCUSDT","recommendation":"SHORT","short_score":90,
              "entry_reference":100,"stop_loss":105,"take_profit_1":90,
              "take_profit_2":95,"timestamp":1700000000000}
        self.assertIsNone(extract_v13_signal(item,"scalp")["tp2_price"])
    def test_extreme_finite_prices_cannot_overflow_persisted_rr(self):
        # Tiny positive risk with an enormous target makes reward/risk
        # overflow even though all individual prices are finite.
        self.assertIsNone(signal(entry_reference=1e-308,stop_loss=5e-309,
                                 take_profit_1=1e308,take_profit_2=None))
    def test_normal_risk_reward_is_finite(self):
        self.assertEqual(signal()["risk_reward"],2.0)

if __name__=="__main__":unittest.main()
