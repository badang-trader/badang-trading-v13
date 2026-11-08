"""Gap and execution-price stress tests for historical research.

A signal candle close must never substitute for the next bar's actual open.
"""
import unittest
from badang_research_backtest_545 import evaluate_signal

class ResearchGapStressTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100.0,"close":100.0} for _ in range(12)]
        self.bars[2]["close"]=100.0
        self.bars[3]["open"]=120.0
        self.bars[6]["close"]=110.0
    def test_long_gap_up_can_lose_despite_exit_above_signal_close(self):
        trade=evaluate_signal(self.bars,2,"long",3,0,0)
        self.assertEqual(trade["actual_entry"],120)
        self.assertEqual(trade["actual_exit"],110)
        self.assertLess(trade["net_return"],0)
    def test_short_gap_up_can_gain_after_entry(self):
        trade=evaluate_signal(self.bars,2,"short",3,0,0)
        self.assertGreater(trade["net_return"],0)
    def test_fees_and_slippage_worsen_gap_trade(self):
        gross=evaluate_signal(self.bars,2,"long",3,0,0)
        net=evaluate_signal(self.bars,2,"long",3,.0006,.0005)
        self.assertLess(net["net_return"],gross["net_return"])
    def test_signal_close_changes_do_not_reprice_entry(self):
        original=evaluate_signal(self.bars,2,"long",3,0,0)
        modified=[dict(b) for b in self.bars]
        modified[2]["close"]=50.0
        updated=evaluate_signal(modified,2,"long",3,0,0)
        self.assertEqual(original["actual_entry"],updated["actual_entry"])
        self.assertEqual(original["net_return"],updated["net_return"])
if __name__=="__main__":unittest.main()
