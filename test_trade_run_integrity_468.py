import unittest
from badang_trade_runs_461 import assess_runs

class AuditRobustnessTests(unittest.TestCase):
    def test_malformed_first_row_does_not_crash(self):
        self.assertEqual(assess_runs([None], 1000, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_short_first_row_does_not_crash(self):
        self.assertEqual(assess_runs([(1,)], 1000, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_duplicate_start_times_fail_closed(self):
        rows = [(100, 110, 'ok'), (100, 120, 'failed')]
        self.assertEqual(assess_runs(rows, 200, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_future_start_is_clock_anomaly(self):
        self.assertEqual(assess_runs([(1100, None, 'running')], 1000, 100)['status'], 'CLOCK_ANOMALY')
    def test_valid_record_still_sample_only(self):
        r = assess_runs([(900, 950, 'ok')], 1000, 100)
        self.assertEqual(r['status'], 'RECENT_OK')
        self.assertFalse(r['coverage_confirmed'])
        self.assertFalse(r['used_in_trading_score'])

if __name__ == '__main__': unittest.main()
