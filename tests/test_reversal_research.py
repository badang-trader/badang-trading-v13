"""Deterministic causal reversal research tests, not a performance claim."""
import unittest
from badang_reversal_research import reversal_candidates

class ReversalTests(unittest.TestCase):
    def test_empty_or_short_history(self):
        self.assertEqual(reversal_candidates([]),[])
        self.assertEqual(reversal_candidates([(i,10,11,9,10,1) for i in range(5)]),[])
    def test_pivots_not_visible_until_confirmation(self):
        # Alternating unambiguous turning points with right=1.
        rows=[(i*1000,100,hi,lo,100,1) for i,(hi,lo) in enumerate([
            (101,99),(105,98),(104,99),(103,90),(104,99),
            (106,98),(104,99),(103,85),(104,99),(108,100),
            (104,99),(103,98)])]
        result=reversal_candidates(rows,left=1,right=1)
        for item in result:
            self.assertGreater(item['available_at_bar'],item['pivot_bar'])
            self.assertEqual(item['elliott_label'],'NOT_CLASSIFIED')
            if item['confirmed_at_bar'] is not None:
                self.assertGreater(item['confirmed_at_bar'],item['available_at_bar'])
            if item['invalidated_at_bar'] is not None:
                self.assertGreater(item['invalidated_at_bar'],item['available_at_bar'])
                self.assertIsNone(item['confirmed_at_bar'])
    def test_no_hindsight_from_appended_rows(self):
        rows=[(i*1000,100,hi,lo,100,1) for i,(hi,lo) in enumerate([
            (101,99),(105,98),(104,99),(103,90),(104,99),
            (106,98),(104,99),(103,85),(104,99),(108,100)])]
        early=reversal_candidates(rows,left=1,right=1)
        later=reversal_candidates(rows+[(10000,100,109,101,108,1)],left=1,right=1)
        for x in early:
            matches=[y for y in later if y['pivot_bar']==x['pivot_bar'] and y['direction']==x['direction']]
            self.assertTrue(matches)
            self.assertEqual(x['available_at_bar'],matches[0]['available_at_bar'])

if __name__=='__main__':unittest.main()
