"""Regression checks for OI collector failure handling without external APIs."""
import unittest
from unittest.mock import patch
from badang_oi_job_444 import collect_once, parse_symbols

class TestOICollectorRetry445(unittest.TestCase):
    def test_failure_does_not_stop_other_symbols(self):
        def observer(symbol):
            if symbol == 'BTCUSDT':
                raise RuntimeError('connection refused')
            return {'status': 'PARTIAL_HISTORY'}
        results = collect_once(['BTCUSDT', 'ETHUSDT'], observer=observer, pause_seconds=0)
        self.assertFalse(results[0]['ok'])
        self.assertTrue(results[1]['ok'])
        self.assertNotIn('connection refused', str(results))
    def test_symbol_deduplication(self):
        self.assertEqual(parse_symbols('btcusdt, BTCUSDT,ethusdt'), ['BTCUSDT','ETHUSDT'])
    def test_reject_invalid_symbol(self):
        with self.assertRaises(ValueError): parse_symbols('BTC-USDT')

if __name__ == '__main__': unittest.main()
