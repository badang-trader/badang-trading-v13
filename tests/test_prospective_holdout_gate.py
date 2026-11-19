import unittest
from badang_prospective_holdout_gate import audit_nonoverlap,cutoff_ms

class ProspectiveHoldoutTests(unittest.TestCase):
    def test_overlapping_bars_rejected(self):
        c=cutoff_ms()
        a=audit_nonoverlap([[c-900000],[c+900000]])
        self.assertFalse(a['independent_period_eligible'])
        self.assertEqual(a['overlap_or_cutoff_bars'],1)
    def test_only_new_bars_temporally_eligible(self):
        c=cutoff_ms()
        a=audit_nonoverlap([[c+900000],[c+1800000]],min_bars=2)
        self.assertTrue(a['independent_period_eligible'])
        self.assertEqual(a['strategy_profitable'],'NOT_ESTABLISHED')
    def test_insufficient_sample_rejected(self):
        c=cutoff_ms()
        self.assertFalse(audit_nonoverlap([[c+900000]],min_bars=2)['independent_period_eligible'])
    def test_duplicates_rejected(self):
        c=cutoff_ms()
        with self.assertRaisesRegex(ValueError,'duplicate'):
            audit_nonoverlap([[c+900000],[c+900000]])

if __name__=='__main__':unittest.main()
