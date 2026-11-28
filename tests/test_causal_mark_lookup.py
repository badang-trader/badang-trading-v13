import unittest
from badang_causal_mark_lookup import observed_mark

class CausalMarkLookupTests(unittest.TestCase):
    def setUp(self):
        self.rows=[[0,100,102,99,101,1],[1800000,101,110,100,109,1]]
    def test_no_future_close(self):
        self.assertEqual(observed_mark(self.rows,'30m',1799999)['status'],
                         'NO_PAST_CLOSED_PRICE')
        self.assertIsNone(observed_mark(self.rows,'30m',1799999)['price'])
    def test_exact_close(self):
        a=observed_mark(self.rows,'30m',1800000)
        self.assertEqual(a['status'],'EXACT_CLOSE')
        self.assertEqual(a['price'],101)
        self.assertEqual(a['age_ms'],0)
    def test_last_past_not_future_candle(self):
        a=observed_mark(self.rows,'30m',2700000)
        self.assertEqual(a['price'],101)
        self.assertEqual(a['age_ms'],900000)
        self.assertFalse(a['eligible_for_strict_equity'])
    def test_stale_flag(self):
        self.assertEqual(observed_mark(self.rows,'30m',2700000,max_age_ms=600000)['status'],
                         'STALE_OBSERVED_CLOSE')
    def test_reject_duplicate(self):
        with self.assertRaisesRegex(ValueError,'duplicated'):
            observed_mark(self.rows+self.rows[:1],'30m',1800000)

if __name__=='__main__':unittest.main()
