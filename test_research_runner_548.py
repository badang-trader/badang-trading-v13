"""Validate sequential research signals, overlap skipping and no lookahead."""
import unittest
from badang_research_runner_548 import evaluate_signals as run

class ResearchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100+i,"close":100+i+0.5} for i in range(30)]
    def test_overlapping_signals_skipped(self):
        s=[{"signal_index":2,"direction":"long"},
           {"signal_index":3,"direction":"short"},
           {"signal_index":7,"direction":"long"}]
        result=run(self.bars,s,horizon=3,fee_per_side=0,slippage_per_side=0)
        self.assertEqual(result["skipped_overlaps"],1)
        self.assertEqual([(t["entry_index"],t["exit_index"]) for t in result["trades"]],[(3,6),(8,11)])
        self.assertEqual(result["summary"]["trades"],2)
    def test_future_candles_do_not_change_past_trade(self):
        s=[{"signal_index":2,"direction":"long"}]
        original=run(self.bars,s,3)
        modified=[dict(x) for x in self.bars]
        modified[15]["close"]=9999
        self.assertEqual(original,run(modified,s,3))
    def test_unsorted_and_duplicate_signals_rejected(self):
        for indices in ([5,4],[5,5]):
            with self.subTest(indices=indices),self.assertRaisesRegex(ValueError,"chronological"):
                run(self.bars,[{"signal_index":i,"direction":"long"} for i in indices])
    def test_empty_signals_have_no_invented_profit(self):
        result=run(self.bars,[])
        self.assertEqual(result,{"trades":[],"skipped_overlaps":0,"summary":None})
    def test_incomplete_future_history_rejected(self):
        with self.assertRaisesRegex(ValueError,"Insufficient"):
            run(self.bars,[{"signal_index":28,"direction":"long"}],3)
if __name__=="__main__":unittest.main()
