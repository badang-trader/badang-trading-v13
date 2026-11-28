"""Causal historical signal evaluation regression tests."""
import unittest
from badang_research_backtest_545 import evaluate_signal as evaluate

class ResearchBacktestTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100+i,"close":100+i+0.5} for i in range(12)]
    def test_next_bar_entry_not_signal_bar_close(self):
        result=evaluate(self.bars,2,"long",horizon=3,fee_per_side=0,slippage_per_side=0)
        self.assertEqual((result["entry_index"],result["exit_index"]),(3,6))
        self.assertEqual(result["actual_entry"],103)
        self.assertEqual(result["actual_exit"],106.5)
    def test_future_changes_cannot_affect_earlier_exit(self):
        a=evaluate(self.bars,2,"long",horizon=3)
        modified=[dict(b) for b in self.bars]
        modified[8]["close"]=999999
        self.assertEqual(a,evaluate(modified,2,"long",horizon=3))
    def test_long_and_short_have_opposite_directional_returns_without_costs(self):
        long=evaluate(self.bars,2,"long",3,0,0)
        short=evaluate(self.bars,2,"short",3,0,0)
        self.assertAlmostEqual(long["net_return"],-short["net_return"])
    def test_insufficient_future_bars_rejected(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):
            evaluate(self.bars,9,"long",2)
    def test_invalid_indices_rejected(self):
        for index,horizon in ((-1,2),(True,2),(2,0),(2,True)):
            with self.assertRaises(ValueError):
                evaluate(self.bars,index,"long",horizon)
if __name__=="__main__":unittest.main()
