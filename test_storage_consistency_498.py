import unittest
from badang_storage_consistency_498 import check_consistency

class Cursor:
    def __init__(self, rows): self.rows=rows
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def execute(self, sql, params):
        assert sql.startswith('SELECT ') and 'UPDATE' not in sql
        assert params == (['BTCUSDT'], 200)
    def fetchall(self): return self.rows
class Conn:
    def __init__(self,rows): self.rows=rows
    def cursor(self): return Cursor(self.rows)
    def close(self): pass
class TestConsistency(unittest.TestCase):
    def check(self,rows): return check_consistency(lambda:Conn(rows),['BTCUSDT'])
    def test_match(self):
        r=self.check([('BTCUSDT',123,[{'id':1}],1)])
        self.assertEqual(r['status'],'SAMPLE_COUNTS_MATCH')
        self.assertFalse(r['trading_ready'])
    def test_mismatch(self): self.assertEqual(self.check([('BTCUSDT',123,[{}],2)])['status'],'COUNT_MISMATCH')
    def test_empty(self): self.assertEqual(self.check([])['status'],'NO_SNAPSHOTS')
    def test_duplicate(self): self.assertEqual(self.check([('BTCUSDT',123,[],0),('BTCUSDT',123,[],0)])['status'],'RECORD_ANOMALY')
    def test_bad_json(self): self.assertEqual(self.check([('BTCUSDT',123,'secret',1)])['status'],'QUERY_FAILED')
    def test_bool_count(self): self.assertEqual(self.check([('BTCUSDT',123,[],False)])['status'],'COUNT_MISMATCH')
    def test_string_json(self): self.assertEqual(self.check([('BTCUSDT',123,'[{"id":1}]',1)])['status'],'SAMPLE_COUNTS_MATCH')
if __name__=='__main__': unittest.main()
