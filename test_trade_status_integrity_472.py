"""Fail-closed integration tests for persisted trade collection status."""
import unittest
from unittest.mock import patch
from test_trade_status_integrity_471 import Connection
from badang_trade_status_458 import collection_status

class Tests(unittest.TestCase):
    def check(self, rows):
        with patch('badang_trade_postgres_454._connection', return_value=Connection(rows)):
            return collection_status('BTCUSDT', now_ms=2000)

    def test_duplicate_fails_closed(self):
        result = self.check([1900, 1900])
        self.assertEqual(result['quality_status'], 'CLOCK_ANOMALY')
        self.assertEqual(result['collection_status'], 'CLOCK_OR_RECORD_ANOMALY')
        self.assertFalse(result['used_in_trading_score'])

    def test_reversed_fails_closed(self):
        self.assertEqual(self.check([1800, 1900])['quality_status'], 'CLOCK_ANOMALY')

    def test_future_fails_closed(self):
        self.assertEqual(self.check([2100])['quality_status'], 'CLOCK_ANOMALY')

    def test_bad_type_fails_closed(self):
        self.assertEqual(self.check(['1900'])['quality_status'], 'CLOCK_ANOMALY')

    def test_valid_data_still_works(self):
        result = self.check([1900, 1800])
        self.assertEqual(result['collection_status'], 'RECENT')
        self.assertFalse(result['is_cvd'])

if __name__ == '__main__': unittest.main()
