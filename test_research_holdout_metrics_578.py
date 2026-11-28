"""Research holdout summaries must not mix development and future results."""
import unittest
from badang_research_holdout_metrics_578 import holdout_performance as evaluate

def trade(s,e,x,r):
    return {"signal_index":s,"entry_index":e,"exit_index":x,"net_return":r}
class HoldoutMetricsTests(unittest.TestCase):
    def test_development_and_holdout_returns_separate(self):
        result=evaluate([trade(1,2,3,.1),trade(6,7,9,-.2)],5,12)
        self.assertAlmostEqual(result["development"]["metrics"]["compounded_net_return"],.1)
        self.assertAlmostEqual(result["holdout"]["metrics"]["compounded_net_return"],-.2)
        self.assertAlmostEqual(result["holdout"]["metrics"]["max_drawdown"],.2)
        self.assertFalse(result["performance_verified"])
    def test_boundary_trade_not_counted_in_either_period(self):
        result=evaluate([trade(3,4,6,.8),trade(7,8,10,-.1)],5,12)
        self.assertEqual(result["boundary_excluded"],1)
        self.assertIsNone(result["development"]["metrics"])
        self.assertEqual(result["holdout"]["completed_trades"],1)
    def test_empty_holdout_does_not_invent_performance(self):
        result=evaluate([trade(1,2,3,.1)],5,12)
        self.assertEqual(result["holdout"]["completed_trades"],0)
        self.assertIsNone(result["holdout"]["metrics"])
        self.assertFalse(result["performance_verified"])
    def test_empty_development_does_not_invent_performance(self):
        result=evaluate([trade(6,7,9,.1)],5,12)
        self.assertIsNone(result["development"]["metrics"])
    def test_invalid_return_rejected(self):
        for value in (float("nan"),float("inf"),-1,True):
            with self.subTest(value=value),self.assertRaises(ValueError):
                evaluate([trade(6,7,9,value)],5,12)
    def test_overlapping_trade_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([trade(1,2,6,.1),trade(6,7,9,.2)],5,12)
if __name__=="__main__":unittest.main()
