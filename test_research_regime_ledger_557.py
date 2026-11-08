"""Regime metrics reject corrupt, overlapping or unsorted trade ledgers."""
import unittest
from badang_research_regime_metrics_556 import summarize_by_regime

class RegimeLedgerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"close":100} for _ in range(80)]
    def trade(self,signal,entry,exit_,ret):
        return {"signal_index":signal,"entry_index":entry,"exit_index":exit_,"net_return":ret}
    def test_overlapping_trades_rejected(self):
        trades=[self.trade(25,26,30,.01),self.trade(27,28,32,.02)]
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,trades)
    def test_unsorted_trades_rejected(self):
        trades=[self.trade(35,36,38,.01),self.trade(25,26,28,.02)]
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,trades)
    def test_invalid_return_rejected(self):
        for ret in (float("nan"),float("inf"),-1.0):
            with self.subTest(ret=ret),self.assertRaises(ValueError):
                summarize_by_regime(self.bars,[self.trade(25,26,28,ret)])
    def test_invalid_timing_rejected(self):
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,[self.trade(25,27,27,.1)])
if __name__=="__main__":unittest.main()
