import tempfile
import unittest
from pathlib import Path
from badang_trade_store_453 import store_snapshot, collection_status


def sample(t, ids):
    return [{'tradeId': str(i), 'symbol': 'BTCUSDT', 'side': 'buy', 'size': '1', 'ts': str(t)} for i in ids]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'samples.db'

    def tearDown(self):
        self.tmp.cleanup()

    def test_persist_across_connections(self):
        store_snapshot(self.path, 'BTCUSDT', sample(1000, [1]), 2000)
        self.assertEqual(collection_status(self.path, 'BTCUSDT')['snapshot_count'], 1)

    def test_overlap(self):
        store_snapshot(self.path, 'BTCUSDT', sample(1000, [1, 2]), 2000)
        r = store_snapshot(self.path, 'BTCUSDT', sample(3000, [2, 3]), 4000)
        self.assertEqual(r['overlap_audit']['status'], 'OVERLAP_OBSERVED')
        self.assertFalse(r['is_cvd'])

    def test_no_overlap_is_not_completeness(self):
        store_snapshot(self.path, 'BTCUSDT', sample(1000, [1]), 2000)
        r = store_snapshot(self.path, 'BTCUSDT', sample(3000, [3]), 4000)
        self.assertEqual(r['overlap_audit']['status'], 'NO_OVERLAP_GAP_UNKNOWN')
        self.assertFalse(r['coverage_confirmed'])

    def test_reject_duplicate_time(self):
        store_snapshot(self.path, 'BTCUSDT', sample(1000, [1]), 2000)
        with self.assertRaises(ValueError):
            store_snapshot(self.path, 'BTCUSDT', sample(1000, [1]), 2000)
        self.assertEqual(collection_status(self.path, 'BTCUSDT')['snapshot_count'], 1)

    def test_reject_invalid_without_writing(self):
        with self.assertRaises(ValueError):
            store_snapshot(self.path, 'BTCUSDT', sample(1000, [1, 1]), 2000)
        self.assertEqual(collection_status(self.path, 'BTCUSDT')['snapshot_count'], 0)

    def test_symbol_separation(self):
        store_snapshot(self.path, 'BTCUSDT', sample(1000, [1]), 2000)
        self.assertEqual(collection_status(self.path, 'ETHUSDT')['snapshot_count'], 0)


if __name__ == '__main__':
    unittest.main()
