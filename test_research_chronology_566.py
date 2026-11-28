"""Reject historical signal streams that are unsorted, duplicated or mistimed."""
import unittest
from badang_research_runner_548 import evaluate_signals
from badang_research_regime_metrics_556 import summarize_by_regime

class ResearchChronologyTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100,"close":100} for _ in range(100)]
    def test_duplicate_signal_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_signals(self.bars,[{"signal_index":30,"direction":"long"},{"signal_index":30,"direction":"short"}])
    def test_reversed_signals_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_signals(self.bars,[{"signal_index":40,"direction":"long"},{"signal_index":30,"direction":"long"}])
    def test_overlapping_signals_skipped_not_double_counted(self):
        signals=[{"signal_index":30,"direction":"long"},{"signal_index":31,"direction":"short"},{"signal_index":36,"direction":"short"}]
        result=evaluate_signals(self.bars,signals,horizon=3)
        self.assertEqual(len(result["trades"]),2)
        self.assertEqual(result["skipped_overlaps"],1)
    def test_post_exit_next_signal_accepted(self):
        signals=[{"signal_index":30,"direction":"long"},{"signal_index":35,"direction":"short"}]
        result=evaluate_signals(self.bars,signals,horizon=3)
        self.assertEqual(len(result["trades"]),2)
    def test_regime_report_rejects_overlapping_trade_records(self):
        trades=[{"signal_index":30,"entry_index":31,"exit_index":35,"net_return":.1},
                {"signal_index":32,"entry_index":33,"exit_index":37,"net_return":.2}]
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,trades)
if __name__=="__main__":unittest.main()
