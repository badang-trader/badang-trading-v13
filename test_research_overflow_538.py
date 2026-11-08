"""Research signal must not emit nonfinite risk/reward for extreme valid OHLC."""
import math
import unittest
from badang_analysis_v13 import analyze

class ResearchOverflowSafetyTests(unittest.TestCase):
    def test_extreme_price_range_never_recommends_or_emits_nan_rr(self):
        rows=[]
        for i in range(205):
            price=1e308 if i%2 else 1e-308
            rows.append([i,price,1e308,1e-308,price,1000])
        result=analyze(rows,mode="swing",symbol="EXTREME")
        self.assertEqual(result["recommendation"],"WAIT")
        self.assertTrue(math.isfinite(result["risk_reward_1"]))

if __name__=="__main__":
    unittest.main()
