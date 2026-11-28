import unittest
from badang_snapshot_progress_482 import check_progress
class Cursor:
 def __init__(self,rows): self.rows=rows;self.calls=[]
 def __enter__(self): return self
 def __exit__(self,*a): return False
 def execute(self,sql,params): self.calls.append((sql,params))
 def fetchall(self): return self.rows
class Conn:
 def __init__(self,rows): self.cur=Cursor(rows);self.closed=False
 def cursor(self): return self.cur
 def close(self): self.closed=True
class Tests(unittest.TestCase):
 def check(self,rows):
  con=Conn(rows)
  result=check_progress(lambda:{'status':'DATABASE_PREFLIGHT_PASSED'},lambda:con,['BTCUSDT','ETHUSDT'],now_ms=100000,max_age_ms=2000,max_gap_ms=5000)
  self.assertTrue(con.closed)
  self.assertIn('ROW_NUMBER()',con.cur.calls[0][0])
  self.assertFalse(result['trading_ready'])
  self.assertFalse(result['coverage_confirmed'])
  return result
 def test_two_recent(self): self.assertEqual(self.check([('BTCUSDT',99000),('BTCUSDT',97000),('ETHUSDT',99500),('ETHUSDT',98000)])['status'],'ALL_TWO_RECENT_SAMPLES_ONLY')
 def test_missing_symbol(self): self.assertEqual(self.check([('BTCUSDT',99000),('BTCUSDT',98000)])['status'],'PROGRESS_INCOMPLETE')
 def test_one_snapshot(self): self.assertEqual(self.check([('BTCUSDT',99000),('ETHUSDT',99500)])['symbols'][0]['status'],'INSUFFICIENT_HISTORY')
 def test_stale(self): self.assertEqual(self.check([('BTCUSDT',90000),('BTCUSDT',88000),('ETHUSDT',99500),('ETHUSDT',99000)])['symbols'][0]['status'],'STALE_SAMPLE')
 def test_gap(self): self.assertEqual(self.check([('BTCUSDT',99000),('BTCUSDT',90000),('ETHUSDT',99500),('ETHUSDT',99000)])['symbols'][0]['status'],'LARGE_SNAPSHOT_GAP')
 def test_duplicate(self): self.assertEqual(self.check([('BTCUSDT',99000),('BTCUSDT',99000)])['status'],'QUERY_FAILED')
 def test_future(self): self.assertEqual(self.check([('BTCUSDT',100001)])['status'],'QUERY_FAILED')
 def test_excess_rows(self): self.assertEqual(self.check([('BTCUSDT',99000),('BTCUSDT',98000),('BTCUSDT',97000)])['status'],'QUERY_FAILED')
 def test_preflight_no_connect(self):
  def forbidden(): raise AssertionError('must not connect')
  self.assertEqual(check_progress(lambda:{'status':'FAIL'},forbidden,['BTCUSDT'],now_ms=100000)['status'],'PREFLIGHT_FAILED')
 def test_secret_hidden(self):
  def broken(): raise RuntimeError('password=secret')
  self.assertNotIn('secret',str(check_progress(lambda:{'status':'DATABASE_PREFLIGHT_PASSED'},broken,['BTCUSDT'],now_ms=100000)))
 def test_invalid_threshold(self): self.assertEqual(check_progress(symbols=['BTCUSDT'],max_gap_ms=0)['status'],'PREFLIGHT_FAILED')
if __name__=='__main__':unittest.main()
