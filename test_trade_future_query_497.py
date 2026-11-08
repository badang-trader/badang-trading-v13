"""Regression: future-dated rows must not be hidden by SQL filtering."""
import unittest
from unittest.mock import patch
from badang_trade_postgres_454 import status

class Cursor:
    def __init__(self, rows): self.rows=rows; self.sql=''; self.args=None
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def execute(self,sql,args=None):
        if 'SELECT fetched_ms FROM' in sql: self.sql=sql; self.args=args
    def fetchall(self):
        if 'fetched_ms<=' in self.sql: return [(x,) for x in self.rows if x<=2000]
        return [(x,) for x in self.rows]
class Connection:
    def __init__(self,rows): self.cur=Cursor(rows)
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def close(self): pass
    def cursor(self): return self.cur
class Tests(unittest.TestCase):
    def test_future_record_not_silently_filtered(self):
        con=Connection([2100,1900])
        with patch('badang_trade_postgres_454._connection',return_value=con):
            result=status('BTCUSDT',now_ms=2000)
        self.assertEqual(result['status'],'CLOCK_OR_RECORD_ANOMALY')
        self.assertNotIn('fetched_ms<=',con.cur.sql)
        self.assertEqual(con.cur.args,('BTCUSDT',))
    def test_valid_history_still_works(self):
        con=Connection([1900,1800])
        with patch('badang_trade_postgres_454._connection',return_value=con):
            result=status('BTCUSDT',now_ms=2000)
        self.assertEqual(result['snapshot_count'],2)
        self.assertFalse(result['coverage_confirmed'])
if __name__=='__main__': unittest.main()
