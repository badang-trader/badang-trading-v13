import unittest
from badang_symbol_freshness_481 import check_symbols

PASS = lambda: {'status': 'DATABASE_PREFLIGHT_PASSED'}
class Cursor:
    def __init__(self, rows): self.rows=rows; self.calls=[]
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params): self.calls.append((sql,params))
    def fetchall(self): return self.rows
class Conn:
    def __init__(self, rows): self.cur=Cursor(rows); self.closed=False
    def cursor(self): return self.cur
    def close(self): self.closed=True

class Tests(unittest.TestCase):
    def run_check(self, rows):
        con=Conn(rows)
        r=check_symbols(PASS,lambda:con,['BTCUSDT','ETHUSDT'],now_ms=100000,max_age_ms=2000)
        self.assertTrue(con.closed)
        self.assertEqual(con.cur.calls[0][1],(['BTCUSDT','ETHUSDT'],))
        self.assertTrue(con.cur.calls[0][0].startswith('SELECT'))
        self.assertFalse(r['trading_ready'])
        return r
    def test_all_recent(self):
        r=self.run_check([('BTCUSDT',99000),('ETHUSDT',99500)])
        self.assertEqual(r['status'],'ALL_RECENT_SAMPLES_ONLY')
        self.assertFalse(r['coverage_confirmed'])
    def test_one_stale_not_masked(self):
        r=self.run_check([('BTCUSDT',99000),('ETHUSDT',80000)])
        self.assertEqual(r['status'],'MISSING_OR_STALE_SAMPLES')
        self.assertEqual(r['symbols'][1]['status'],'NO_RECENT_SAMPLE')
    def test_one_missing_not_masked(self):
        self.assertEqual(self.run_check([('BTCUSDT',99000)])['status'],'MISSING_OR_STALE_SAMPLES')
    def test_duplicate_rows_fail_closed(self):
        self.assertEqual(self.run_check([('BTCUSDT',99000),('BTCUSDT',98000)])['status'],'QUERY_FAILED')
    def test_future_timestamp_fail_closed(self):
        self.assertEqual(self.run_check([('BTCUSDT',100001)])['status'],'QUERY_FAILED')
    def test_unknown_symbol_fail_closed(self):
        self.assertEqual(self.run_check([('DOGEUSDT',99000)])['status'],'QUERY_FAILED')
    def test_preflight_prevents_connection(self):
        def forbidden(): raise AssertionError('should not connect')
        r=check_symbols(lambda:{'status':'DATABASE_FAILED'},forbidden,['BTCUSDT'],now_ms=100000)
        self.assertEqual(r['status'],'PREFLIGHT_FAILED')
    def test_error_secrets_hidden(self):
        def fail(): raise RuntimeError('password=secret123')
        r=check_symbols(PASS,fail,['BTCUSDT'],now_ms=100000)
        self.assertNotIn('secret123',str(r))
    def test_invalid_symbols_fail_closed(self):
        r=check_symbols(PASS,lambda:Conn([]),['BTCUSDT','BTCUSDT'],now_ms=100000)
        self.assertEqual(r['status'],'PREFLIGHT_FAILED')
if __name__=='__main__': unittest.main()
