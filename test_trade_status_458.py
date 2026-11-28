import unittest
from unittest.mock import patch
from badang_trade_status_458 import collection_status

class TestCollectionStatus(unittest.TestCase):
    @patch('badang_trade_status_458.status')
    def test_recent(self, status):
        status.return_value = {'latest_age_ms': 2000, 'snapshot_count': 2}
        x=collection_status('BTCUSDT')
        self.assertEqual(x['collection_status'], 'RECENT')
        self.assertFalse(x['is_cvd'])
        self.assertFalse(x['coverage_confirmed'])
        self.assertFalse(x['continuous_collection_verified'])
    @patch('badang_trade_status_458.status')
    def test_stale(self, status):
        status.return_value = {'latest_age_ms': 180001, 'snapshot_count': 2, 'largest_collection_gap_ms': 60000}
        self.assertEqual(collection_status('ETHUSDT')['collection_status'],'STALE')
    @patch('badang_trade_status_458.status')
    def test_empty(self, status):
        status.return_value = {'latest_age_ms': None, 'snapshot_count': 0, 'largest_collection_gap_ms': None}
        self.assertEqual(collection_status('ETHUSDT')['collection_status'],'NO_RECORDS')
    @patch('badang_trade_status_458.status')
    def test_future_timestamp(self, status):
        status.return_value = {'latest_age_ms': -1, 'snapshot_count': 2, 'largest_collection_gap_ms': 60000}
        self.assertEqual(collection_status('ETHUSDT')['collection_status'],'STALE')
    def test_bad_threshold(self):
        with self.assertRaises(ValueError):collection_status('BTCUSDT',recent_threshold_ms=0)

if __name__=='__main__': unittest.main()
