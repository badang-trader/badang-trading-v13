"""Ensure read endpoints commit their schema initialization transaction."""
import unittest
from unittest.mock import patch


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, *args): pass
    def fetchall(self): return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.committed = False
        self.closed = False
    def __enter__(self): return self
    def __exit__(self, kind, value, tb):
        self.committed = kind is None
        return False
    def cursor(self): return FakeCursor(self.rows)
    def close(self): self.closed = True


class ReadTransactionTests(unittest.TestCase):
    def test_worker_status_commits_initial_schema(self):
        from badang_trade_runs_461 import latest_status
        con = FakeConnection([])
        with patch('badang_trade_config_460.poll_interval_seconds', return_value=30):
            result = latest_status(now_ms=100000, connect=lambda: con)
        self.assertEqual(result['status'], 'NO_RUNS')
        self.assertTrue(con.committed)
        self.assertTrue(con.closed)

    def test_snapshot_status_commits_initial_schema(self):
        from badang_trade_postgres_454 import status
        con = FakeConnection([])
        with patch('badang_trade_postgres_454._connection', return_value=con):
            result = status('BTCUSDT', now_ms=100000)
        self.assertEqual(result['snapshot_count'], 0)
        self.assertTrue(con.committed)
        self.assertTrue(con.closed)


if __name__ == '__main__':
    unittest.main()
