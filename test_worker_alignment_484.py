"""Regression tests: worker success alone must not certify snapshot provenance."""
import unittest
from badang_worker_crosscheck_483 import crosscheck
from test_worker_crosscheck_483 import Connection, NOW

RUN = [(98000, 99000, 'ok')]

def check(samples, status='ALL_TWO_RECENT_SAMPLES_ONLY'):
    return crosscheck(lambda: {'status': status, 'symbols': samples}, lambda: Connection(RUN), NOW, 5000)

def sample(name, stamp):
    return {'symbol': name, 'status': 'TWO_RECENT_SAMPLES_ONLY', 'latest_fetched_ms': stamp}

class Tests(unittest.TestCase):
    def test_aligned(self):
        result = check([sample('BTCUSDT', 98500), sample('ETHUSDT', 98700)])
        self.assertTrue(result['latest_run_snapshot_aligned'])
        self.assertEqual(result['status'], 'RECENT_SAMPLES_AND_WORKER_ONLY')
    def test_snapshot_before_latest_run(self):
        self.assertEqual(check([sample('BTCUSDT', 97500)])['status'], 'WORKER_OR_SNAPSHOT_WARNING')
    def test_snapshot_after_latest_run(self):
        self.assertFalse(check([sample('BTCUSDT', 99500)])['latest_run_snapshot_aligned'])
    def test_missing_provenance(self):
        self.assertFalse(check([])['latest_run_snapshot_aligned'])
    def test_duplicate_symbol(self):
        self.assertFalse(check([sample('BTCUSDT', 98500), sample('BTCUSDT', 98700)])['latest_run_snapshot_aligned'])
    def test_invalid_timestamp(self):
        self.assertFalse(check([sample('BTCUSDT', True)])['latest_run_snapshot_aligned'])
    def test_missing_symbols_key(self):
        result = crosscheck(lambda: {'status':'ALL_TWO_RECENT_SAMPLES_ONLY'}, lambda: Connection(RUN), NOW, 5000)
        self.assertEqual(result['status'], 'WORKER_OR_SNAPSHOT_WARNING')

if __name__ == '__main__': unittest.main()
