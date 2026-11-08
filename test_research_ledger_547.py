"""Reject overlapping and nonchronological research trades."""
import unittest
from badang_research_ledger_547 import summarize_nonoverlapping_trades as summary

class ResearchLedgerTests(unittest.TestCase):
    def test_sequential_trades_compound(self):
        result=summary([{"entry_index":1,"exit_index":3,"net_return":0.1},
                        {"entry_index":4,"exit_index":7,"net_return":-0.1}])
        self.assertEqual(result["trades"],2)
        self.assertAlmostEqual(result["compounded_net_return"],-0.01)
    def test_overlapping_trades_rejected(self):
        for second in (2,3):
            with self.subTest(second=second),self.assertRaisesRegex(ValueError,"Overlapping"):
                summary([{"entry_index":1,"exit_index":3,"net_return":0.1},
                         {"entry_index":second,"exit_index":5,"net_return":0.2}])
    def test_unsorted_trades_rejected(self):
        with self.assertRaisesRegex(ValueError,"Overlapping"):
            summary([{"entry_index":5,"exit_index":7,"net_return":0.1},
                     {"entry_index":1,"exit_index":3,"net_return":0.1}])
    def test_invalid_timing_rejected(self):
        for entry,exit_index in ((-1,2),(2,2),(3,2),(True,4)):
            with self.subTest(entry=entry,exit_index=exit_index),self.assertRaises(ValueError):
                summary([{"entry_index":entry,"exit_index":exit_index,"net_return":0.1}])
    def test_missing_return_rejected(self):
        with self.assertRaisesRegex(ValueError,"Missing"):
            summary([{"entry_index":1,"exit_index":3}])
    def test_invalid_return_rejected(self):
        with self.assertRaises(ValueError):
            summary([{"entry_index":1,"exit_index":3,"net_return":float("nan")}])
if __name__=="__main__":unittest.main()
