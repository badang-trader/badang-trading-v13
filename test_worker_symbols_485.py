"""Ensure a partial/forged symbol list cannot pass worker alignment."""
import unittest
from unittest.mock import patch
from badang_worker_crosscheck_483 import crosscheck
from test_worker_crosscheck_483 import Connection, NOW

def assess(samples):
    con = Connection([(98000, 99000, 'ok')])
    with patch('badang_worker_crosscheck_483.symbols_from_env', return_value=['BTCUSDT', 'ETHUSDT']):
        return crosscheck(lambda: {'status': 'ALL_TWO_RECENT_SAMPLES_ONLY', 'symbols': samples},
                          lambda: con, NOW, 5000)

def sample(name, stamp=98500):
    return {'symbol': name, 'status': 'TWO_RECENT_SAMPLES_ONLY', 'latest_fetched_ms': stamp}

class Tests(unittest.TestCase):
    def test_complete_expected_set_passes(self):
        self.assertEqual(assess([sample('BTCUSDT'), sample('ETHUSDT')])['status'],
                         'RECENT_SAMPLES_AND_WORKER_ONLY')
    def test_missing_eth_fails_closed(self):
        self.assertEqual(assess([sample('BTCUSDT')])['status'], 'WORKER_OR_SNAPSHOT_WARNING')
    def test_unexpected_symbol_fails_closed(self):
        self.assertEqual(assess([sample('BTCUSDT'), sample('ETHUSDT'), sample('SOLUSDT')])['status'],
                         'WORKER_OR_SNAPSHOT_WARNING')
    def test_duplicate_symbol_fails_closed(self):
        self.assertEqual(assess([sample('BTCUSDT'), sample('BTCUSDT')])['status'],
                         'WORKER_OR_SNAPSHOT_WARNING')
    def test_empty_symbols_fails_closed(self):
        self.assertEqual(assess([])['status'], 'WORKER_OR_SNAPSHOT_WARNING')
    def test_orders_never_enabled(self):
        result = assess([sample('BTCUSDT'), sample('ETHUSDT')])
        self.assertFalse(result['safe_to_enable_orders'])
        self.assertFalse(result['trading_ready'])

if __name__ == '__main__': unittest.main()
