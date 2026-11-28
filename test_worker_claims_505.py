"""Reject malformed or unsupported safety claims in REST sample diagnostics."""
import unittest
from badang_worker_crosscheck_483 import crosscheck
from test_worker_crosscheck_483 import Connection, NOW, progress

class ClaimTests(unittest.TestCase):
    def test_progress_nonboolean_claim_fails_before_database(self):
        for claim in ('yes', 1, None, [], {}):
            with self.subTest(claim=claim):
                def no_db(): raise AssertionError('DB must not be touched')
                def bad(): return {**progress()(), 'coverage_confirmed': claim}
                self.assertEqual(crosscheck(bad, no_db, NOW)['status'], 'UNSUPPORTED_READINESS_CLAIM')
    def test_progress_new_claims_fail(self):
        for key in ('is_cvd', 'used_in_trading_score'):
            def no_db(): raise AssertionError('DB must not be touched')
            def bad(): return {**progress()(), key: True}
            self.assertEqual(crosscheck(bad, no_db, NOW)['status'], 'UNSUPPORTED_READINESS_CLAIM')
    def test_symbol_claim_prevents_success(self):
        for claim in (True, 'true', 1, None):
            with self.subTest(claim=claim):
                def bad():
                    r=progress()()
                    r['symbols'][0]['used_in_trading_score']=claim
                    return r
                r=crosscheck(bad, lambda: Connection([(98000,99000,'ok')]), NOW, 5000)
                self.assertEqual(r['status'], 'WORKER_OR_SNAPSHOT_WARNING')
                self.assertFalse(r['latest_run_snapshot_aligned'])
    def test_explicit_false_is_accepted(self):
        def safe():
            r=progress()()
            r['is_cvd']=False
            r['symbols'][0]['used_in_trading_score']=False
            return r
        r=crosscheck(safe, lambda: Connection([(98000,99000,'ok')]), NOW, 5000)
        self.assertEqual(r['status'], 'RECENT_SAMPLES_AND_WORKER_ONLY')

if __name__ == '__main__': unittest.main()
