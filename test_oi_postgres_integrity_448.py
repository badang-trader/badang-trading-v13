"""Regression tests for durable OI history, without Flask or a live database."""
import unittest
from unittest.mock import patch
import badang_oi_postgres_443 as target

NOW = 1_800_000_000_000

class Cursor:
    def __init__(self, rows): self.rows=rows
    def execute(self,*args): pass
    def fetchall(self): return self.rows
    def __enter__(self): return self
    def __exit__(self,*args): pass

class Connection:
    def __init__(self,rows): self.rows=rows
    def cursor(self): return Cursor(self.rows)
    def close(self): pass

class OIIntegrityTests(unittest.TestCase):
    def read(self,rows):
        with patch.object(target,'_connection',return_value=Connection(rows)):
            return target.changes('BTCUSDT',now_ms=NOW)
    def test_full_history(self):
        r=self.read([(NOW-1000,100),(NOW-901000,80),(NOW-3601000,50)])
        self.assertEqual(r['status'],'HISTORY_AVAILABLE')
        self.assertEqual(r['oi_change_15m_pct'],25)
        self.assertEqual(r['oi_change_1h_pct'],100)
    def test_future_only_observation_rejected(self):
        self.assertEqual(self.read([(NOW+1000,100)])['status'],'STALE_OR_MISSING_CURRENT')
    def test_stale_current_rejected(self):
        self.assertEqual(self.read([(NOW-181000,100)])['status'],'STALE_OR_MISSING_CURRENT')
    def test_corrupt_baseline_ignored(self):
        r=self.read([(NOW-1000,100),(NOW-901000,0),(NOW-3601000,50)])
        self.assertIsNone(r['oi_change_15m_pct'])
        self.assertEqual(r['oi_change_1h_pct'],100)
    def test_missing_history(self):
        self.assertEqual(self.read([])['status'],'STALE_OR_MISSING_CURRENT')

if __name__=='__main__': unittest.main()
