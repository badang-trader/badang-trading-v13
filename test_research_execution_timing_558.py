"""Regime metrics reject inconsistent signal/entry/exit indices."""
import unittest
from badang_research_regime_metrics_556 import summarize_by_regime

class ResearchExecutionTimingTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"close":100} for _ in range(60)]
    def test_next_open_entry_required(self):
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,[{"signal_index":25,"entry_index":27,
                                           "exit_index":29,"net_return":.01}])
    def test_exit_must_be_in_available_history(self):
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,[{"signal_index":55,"entry_index":56,
                                           "exit_index":60,"net_return":.01}])
    def test_valid_next_open_trade(self):
        result=summarize_by_regime(self.bars,[{"signal_index":25,"entry_index":26,
                                               "exit_index":29,"net_return":.01}])
        self.assertEqual(result["sideways"]["trade_count"],1)
    def test_bool_signal_index_rejected(self):
        with self.assertRaises(ValueError):
            summarize_by_regime(self.bars,[{"signal_index":True,"entry_index":2,
                                           "exit_index":3,"net_return":.01}])
if __name__=="__main__":unittest.main()
