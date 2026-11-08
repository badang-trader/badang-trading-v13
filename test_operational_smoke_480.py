import unittest
from badang_operational_smoke_480 import smoke

PASS = lambda: {'status': 'DATABASE_PREFLIGHT_PASSED'}
class Cursor:
    def __init__(self, row): self.row=row; self.sql=[]
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql): self.sql.append(sql)
    def fetchone(self): return self.row
class Connection:
    def __init__(self, row): self.cur=Cursor(row); self.closed=False
    def cursor(self): return self.cur
    def close(self): self.closed=True

class OperationalSmokeTests(unittest.TestCase):
    def test_preflight_failure_does_not_connect(self):
        def forbidden(): raise AssertionError('should not connect')
        self.assertEqual(smoke(lambda: {'status':'DATABASE_FAILED'}, forbidden)['status'],'PREFLIGHT_FAILED')
    def test_recent_sample_not_cvd_or_trading_ready(self):
        con=Connection((99000,))
        r=smoke(PASS, lambda: con, now_ms=100000, max_age_ms=2000)
        self.assertEqual(r['status'],'RECENT_SAMPLE_ONLY')
        self.assertFalse(r['coverage_confirmed']); self.assertFalse(r['trading_ready'])
        self.assertTrue(con.closed)
        self.assertTrue(all(s.strip().upper().startswith('SELECT') for s in con.cur.sql))
    def test_stale_sample(self):
        r=smoke(PASS, lambda: Connection((90000,)), now_ms=100000, max_age_ms=2000)
        self.assertEqual(r['status'],'NO_RECENT_SAMPLE')
    def test_empty_table(self):
        r=smoke(PASS, lambda: Connection((None,)), now_ms=100000)
        self.assertEqual(r['status'],'NO_RECENT_SAMPLE')
    def test_future_timestamp_fails_closed(self):
        r=smoke(PASS, lambda: Connection((100001,)), now_ms=100000)
        self.assertEqual(r['status'],'SNAPSHOT_QUERY_FAILED')
    def test_malformed_timestamp_fails_closed(self):
        r=smoke(PASS, lambda: Connection(('100000',)), now_ms=100000)
        self.assertEqual(r['status'],'SNAPSHOT_QUERY_FAILED')
    def test_secrets_not_exposed(self):
        def secret(): raise RuntimeError('password=private')
        r=smoke(PASS, secret, now_ms=100000)
        self.assertNotIn('private',str(r))
    def test_invalid_threshold_fails_closed(self):
        r=smoke(PASS, lambda: Connection((99000,)), now_ms=100000, max_age_ms=0)
        self.assertEqual(r['status'],'PREFLIGHT_FAILED')
if __name__=='__main__': unittest.main()
