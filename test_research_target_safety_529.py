"""Recommendation cannot be LONG/SHORT if projected targets are nonpositive."""
import unittest
from badang_analysis_v13 import analyze

class ResearchTargetSafetyTests(unittest.TestCase):
    def test_deep_decline_cannot_recommend_negative_short_target(self):
        rows=[]
        for i in range(205):
            close=100.0-(99.8*i/204)
            rows.append([i,close,close+0.2,max(0.00001,close-0.2),close,1000])
        result=analyze(rows,mode="swing",symbol="TESTUSDT")
        self.assertEqual(result["status"],"ok")
        if result["candidate_side"]=="SHORT" and result["take_profit_1"]<=0:
            self.assertEqual(result["recommendation"],"WAIT")
        if result["recommendation"] in ("LONG","SHORT"):
            levels=[result["entry_reference"],result["stop_loss"],result["take_profit_1"],result["take_profit_2"]]
            self.assertTrue(all(x>0 for x in levels))
    def test_no_recommendation_from_flat_zero_atr_market(self):
        rows=[[i,100,100,100,100,1000] for i in range(205)]
        result=analyze(rows)
        self.assertEqual(result["recommendation"],"WAIT")
        self.assertEqual(result["status"],"ok")

if __name__=="__main__":unittest.main()
