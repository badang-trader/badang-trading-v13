"""Verify completed-trade holdout partition cannot leak boundary outcomes."""
import unittest
from badang_research_holdout_partition_577 import partition_completed_trades as partition

def trade(s,e,x):
    return {"signal_index":s,"entry_index":e,"exit_index":x}
class HoldoutPartitionTests(unittest.TestCase):
    def test_clean_split(self):
        result=partition([trade(1,2,4),trade(6,7,9)],5,12)
        self.assertEqual(len(result["development"]),1)
        self.assertEqual(len(result["holdout"]),1)
        self.assertEqual(result["boundary_excluded"],0)
    def test_boundary_crossing_trade_excluded(self):
        result=partition([trade(2,3,6),trade(7,8,10)],5,12)
        self.assertEqual(result["boundary_excluded"],1)
        self.assertEqual(result["development"],[])
        self.assertEqual(len(result["holdout"]),1)
    def test_signal_before_split_not_holdout_even_if_entry_after(self):
        result=partition([trade(4,5,7)],5,12)
        self.assertEqual(result["holdout"],[])
        self.assertEqual(result["boundary_excluded"],1)
    def test_reject_overlap_and_reversed_chronology(self):
        for trades in ([trade(1,2,5),trade(5,6,7)],[trade(4,5,6),trade(1,2,3)],[trade(3,3,5)]):
            with self.subTest(trades=trades),self.assertRaises(ValueError):
                partition(trades,5,12)
    def test_reject_invalid_boundaries(self):
        for split,total in ((0,12),(12,12),(1,1),(True,12),(5,False),(5,4)):
            with self.subTest(split=split,total=total),self.assertRaises(ValueError):
                partition([],split,total)
    def test_reject_invalid_trade_indices(self):
        for value in (True,1.5,None,-1,12):
            with self.subTest(value=value),self.assertRaises(ValueError):
                partition([trade(value,3,4)],5,12)
if __name__=="__main__":unittest.main()
