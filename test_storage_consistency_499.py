import unittest
from badang_storage_consistency_498 import check_consistency, SQL

class Cursor:
    def __init__(self, rows): self.rows=rows
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params):
        assert sql == SQL
        assert params == (['BTCUSDT', 'ETHUSDT'], 200)
    def fetchall(self): return self.rows
class Conn:
    def __init__(self, rows): self.rows=rows
    def cursor(self): return Cursor(self.rows)
    def close(self): pass
class TestPerSymbol(unittest.TestCase):
    def check(self, rows): return check_consistency(lambda: Conn(rows), ['BTCUSDT','ETHUSDT'])
    def test_both_present(self):
        r=self.check([('BTCUSDT',10,[],0),('ETHUSDT',11,[{}],1)])
        self.assertEqual(r['status'], 'SAMPLE_COUNTS_MATCH')
        self.assertEqual(r['missing_symbols'], [])
    def test_eth_missing(self):
        r=self.check([('BTCUSDT',10,[],0)])
        self.assertEqual(r['status'], 'MISSING_SYMBOLS')
        self.assertEqual(r['missing_symbols'], ['ETHUSDT'])
        self.assertFalse(r['trading_ready'])
    def test_btc_missing(self):
        self.assertEqual(self.check([('ETHUSDT',11,[],0)])['missing_symbols'], ['BTCUSDT'])
    def test_empty(self):
        self.assertEqual(self.check([])['status'], 'NO_SNAPSHOTS')
    def test_partitioned_query(self):
        self.assertIn('PARTITION BY symbol', SQL)
        self.assertIn('rn <= %s', SQL)
    def test_mismatch_precedes_missing(self):
        self.assertEqual(self.check([('BTCUSDT',10,[{}],0)])['status'], 'COUNT_MISMATCH')
if __name__ == '__main__': unittest.main()
