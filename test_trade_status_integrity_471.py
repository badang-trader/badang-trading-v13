"""Bounded-history and fail-closed tests for PostgreSQL trade status."""
import unittest
from unittest.mock import patch
from badang_trade_postgres_454 import status

class Cursor:
    def __init__(self, rows): self.rows=rows
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def execute(self,*args): pass
    def fetchall(self): return [(x,) for x in self.rows]
class Connection:
    def __init__(self,rows): self.rows=rows
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def close(self): pass
    def cursor(self): return Cursor(self.rows)
class Tests(unittest.TestCase):
    def check(self,rows):
        with patch('badang_trade_postgres_454._connection',return_value=Connection(rows)):
            return status('BTCUSDT',now_ms=2000)
    def test_bounded_count_not_total(self):
        result=self.check(list(range(2000,1000,-1)))
        self.assertEqual(result['snapshot_count'],1000)
        self.assertTrue(result['history_truncated_or_at_limit'])
        self.assertEqual(result['gap_scope'],'last_1000_snapshots_only')
        self.assertFalse(result['is_cvd'])
    def test_empty(self):
        self.assertEqual(self.check([])['snapshot_count'],0)
    def test_duplicate_timestamp_fail_closed(self):
        self.assertEqual(self.check([1900,1900])['status'],'CLOCK_OR_RECORD_ANOMALY')
    def test_reversed_timestamp_fail_closed(self):
        self.assertEqual(self.check([1800,1900])['status'],'CLOCK_OR_RECORD_ANOMALY')
    def test_future_timestamp_fail_closed(self):
        self.assertEqual(self.check([2100])['status'],'CLOCK_OR_RECORD_ANOMALY')
    def test_invalid_observation_clock(self):
        with self.assertRaises(ValueError): status('BTCUSDT',now_ms=0)

if __name__=='__main__': unittest.main()
