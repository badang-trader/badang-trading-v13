import unittest
from badang_trade_runs_461 import assess_runs

class RunIntegrityTests(unittest.TestCase):
    def test_previous_unfinished_after_success(self):
        result = assess_runs([(300, 350, 'ok'), (100, None, 'running')], 400, 100)
        self.assertEqual(result['status'], 'RECENT_OK')
        self.assertTrue(result['previous_run_unfinished'])
        self.assertFalse(result['restart_verified'])
        self.assertFalse(result['coverage_confirmed'])
    def test_completed_missing_finish_is_invalid(self):
        self.assertEqual(assess_runs([(100, None, 'ok')], 200, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_running_with_finish_is_invalid(self):
        self.assertEqual(assess_runs([(100, 150, 'running')], 200, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_future_finish_is_invalid(self):
        self.assertEqual(assess_runs([(100, 300, 'ok')], 200, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_reversed_order_is_invalid(self):
        self.assertEqual(assess_runs([(100, 150, 'ok'), (200, 250, 'ok')], 300, 100)['status'], 'CLOCK_OR_RECORD_ANOMALY')
    def test_invalid_clock_rejected(self):
        with self.assertRaises(ValueError): assess_runs([], 0, 100)
    def test_stale_old_running(self):
        self.assertEqual(assess_runs([(100, None, 'running')], 500, 100)['status'], 'INTERRUPTED_OR_RUNNING')

if __name__ == '__main__': unittest.main()
