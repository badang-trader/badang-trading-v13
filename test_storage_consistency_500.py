import unittest
from badang_storage_consistency_498 import check_consistency
class Cursor:
    def __init__(self, rows): self.rows=rows
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,params): pass
    def fetchall(self): return self.rows
class Conn:
    def __init__(self,rows): self.rows=rows
    def cursor(self): return Cursor(self.rows)
    def close(self): pass
class Tests(unittest.TestCase):
    def check(self,rows,now=1000): return check_consistency(lambda:Conn(rows),['BTCUSDT','ETHUSDT'],now_ms=now)
    def test_valid(self): self.assertEqual(self.check([('BTCUSDT',900,[],0),('BTCUSDT',800,[],0),('ETHUSDT',950,[],0)])['status'],'SAMPLE_COUNTS_MATCH')
    def test_future(self): self.assertEqual(self.check([('BTCUSDT',1001,[],0),('ETHUSDT',900,[],0)])['status'],'RECORD_ANOMALY')
    def test_equal_now(self): self.assertEqual(self.check([('BTCUSDT',1000,[],0),('ETHUSDT',1000,[],0)])['status'],'SAMPLE_COUNTS_MATCH')
    def test_wrong_order(self): self.assertEqual(self.check([('BTCUSDT',800,[],0),('BTCUSDT',900,[],0),('ETHUSDT',950,[],0)])['status'],'RECORD_ANOMALY')
    def test_bad_clock(self): self.assertEqual(self.check([],True)['status'],'QUERY_FAILED')
    def test_no_trading_claim(self):
        r=self.check([('BTCUSDT',900,[],0),('ETHUSDT',900,[],0)])
        self.assertIs(r['trading_ready'],False)
        self.assertIs(r['coverage_confirmed'],False)
if __name__=='__main__': unittest.main()
