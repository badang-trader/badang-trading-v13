import unittest
from badang_worker_crosscheck_483 import crosscheck

NOW = 100000

def progress(status='ALL_TWO_RECENT_SAMPLES_ONLY'):
    return lambda: {'status': status, 'symbols': [{'symbol':'BTCUSDT', 'status':'TWO_RECENT_SAMPLES_ONLY', 'latest_fetched_ms':98500}, {'symbol':'ETHUSDT', 'status':'TWO_RECENT_SAMPLES_ONLY', 'latest_fetched_ms':98700}]}

class Cursor:
    def __init__(self, rows): self.rows = rows; self.sql = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql): self.sql = sql
    def fetchall(self): return self.rows

class Connection:
    def __init__(self, rows): self.cur = Cursor(rows); self.closed = False
    def cursor(self): return self.cur
    def close(self): self.closed = True

class Tests(unittest.TestCase):
    def check(self, rows, snapshot='ALL_TWO_RECENT_SAMPLES_ONLY'):
        con = Connection(rows)
        result = crosscheck(progress(snapshot), lambda: con, NOW, 5000)
        self.assertTrue(con.closed)
        self.assertIn('SELECT', con.cur.sql)
        self.assertNotIn('CREATE', con.cur.sql)
        self.assertFalse(result['trading_ready'])
        self.assertFalse(result['continuous_cvd_verified'])
        self.assertFalse(result['safe_to_enable_orders'])
        return result
    def test_recent_worker_and_snapshots(self):
        self.assertEqual(self.check([(98000,99000,'ok')])['status'], 'RECENT_SAMPLES_AND_WORKER_ONLY')
    def test_stale_worker(self):
        self.assertEqual(self.check([(90000,92000,'ok')])['status'], 'WORKER_OR_SNAPSHOT_WARNING')
    def test_failed_worker(self):
        self.assertEqual(self.check([(98000,99000,'failed')])['worker_status'], 'FAILED')
    def test_unfinished_previous(self):
        self.assertEqual(self.check([(98000,99000,'ok'),(90000,None,'running')])['status'], 'WORKER_OR_SNAPSHOT_WARNING')
    def test_stale_snapshot(self):
        self.assertEqual(self.check([(98000,99000,'ok')], 'PROGRESS_INCOMPLETE')['status'], 'WORKER_OR_SNAPSHOT_WARNING')
    def test_no_worker_runs(self):
        self.assertEqual(self.check([])['worker_status'], 'NO_RUNS')
    def test_preflight_failure_does_not_connect(self):
        def forbidden(): raise AssertionError('connection must not happen')
        self.assertEqual(crosscheck(progress('PREFLIGHT_FAILED'), forbidden, NOW)['status'], 'SNAPSHOT_CHECK_FAILED')
    def test_secret_hidden(self):
        def broken(): raise RuntimeError('password=supersecret')
        self.assertNotIn('supersecret', str(crosscheck(progress(), broken, NOW)))
    def test_invalid_clock(self):
        self.assertEqual(crosscheck(progress(), now_ms=True)['status'], 'CHECK_FAILED')

if __name__ == '__main__': unittest.main()
