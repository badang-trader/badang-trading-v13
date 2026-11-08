import unittest
from badang_worker_crosscheck_483 import crosscheck

class ReadOnlyTests(unittest.TestCase):
    def test_explicit_write_source_rejected_before_database(self):
        for flag in (False, 'true', 1, None):
            with self.subTest(flag=flag):
                def forbidden(): raise AssertionError('database must not be opened')
                r = crosscheck(lambda: {'status':'ALL_TWO_RECENT_SAMPLES_ONLY','read_only':flag}, forbidden, 100000)
                self.assertEqual(r['status'], 'UNSAFE_SNAPSHOT_SOURCE')
                self.assertIs(r['trading_ready'], False)
    def test_legacy_no_readonly_marker_remains_compatible(self):
        r = crosscheck(lambda: {'status':'PREFLIGHT_FAILED'}, now_ms=100000)
        self.assertEqual(r['status'], 'SNAPSHOT_CHECK_FAILED')

if __name__=='__main__': unittest.main()
