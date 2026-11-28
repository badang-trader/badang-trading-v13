import unittest
from badang_real_pivot_audit import confirmed_pivots
class CausalPivotTests(unittest.TestCase):
    def test_confirmation_is_three_bars_later(self):
        highs=[2,3,4,9,4,3,2,3,2]
        rows=[[i*900000,2,h,1,2,1] for i,h in enumerate(highs)]
        pivots=confirmed_pivots(rows)
        p=[x for x in pivots if x['pivot_bar']==3 and x['type']=='HIGH']
        self.assertEqual(len(p),1)
        self.assertEqual(p[0]['confirmed_at_bar'],6)
    def test_unconfirmed_recent_peak_not_reported(self):
        rows=[[i*900000,2,2+i,1,2,1] for i in range(8)]
        self.assertFalse(any(p['type']=='HIGH' for p in confirmed_pivots(rows)))
    def test_tied_peak_is_not_unique(self):
        highs=[2,3,4,9,9,3,2,3,2]
        rows=[[i*900000,2,h,1,2,1] for i,h in enumerate(highs)]
        self.assertFalse(any(p['pivot_bar'] in (3,4) and p['type']=='HIGH'
                             for p in confirmed_pivots(rows)))
if __name__=='__main__':unittest.main()
