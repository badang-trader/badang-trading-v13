import unittest
from badang_db_schema_474 import REQUIRED, inspect_schema

class Cursor:
    def __init__(self, rows, error=None):
        self.rows, self.error, self.calls = rows, error, []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params):
        self.calls.append((query, params))
        if self.error: raise RuntimeError('SECRET_DB_PASSWORD')
    def fetchall(self): return self.rows

class Connection:
    def __init__(self, cursor): self.cur, self.closed = cursor, False
    def cursor(self): return self.cur
    def close(self): self.closed = True

class SchemaTests(unittest.TestCase):
    def rows(self):
        return [(table, col, dtype) for table, cols in REQUIRED.items() for col, dtype in cols.items()]
    def test_complete(self):
        cursor=Cursor(self.rows()); con=Connection(cursor)
        result=inspect_schema(lambda:con)
        self.assertTrue(result['schema_compatible']); self.assertFalse(result['trading_ready'])
        self.assertTrue(con.closed)
        self.assertEqual(len(cursor.calls),1)
        self.assertIn('information_schema.columns',cursor.calls[0][0])
    def test_missing_column(self):
        result=inspect_schema(lambda:Connection(Cursor(self.rows()[1:])))
        self.assertFalse(result['schema_compatible']); self.assertIn('symbol',result['mismatches']['badang_trade_snapshots'])
    def test_wrong_type(self):
        rows=self.rows(); rows[0]=(rows[0][0],rows[0][1],'integer')
        result=inspect_schema(lambda:Connection(Cursor(rows)))
        self.assertFalse(result['schema_compatible'])
    def test_error_redacted(self):
        con=Connection(Cursor([],error=True)); result=inspect_schema(lambda:con)
        self.assertFalse(result['schema_compatible']); self.assertTrue(con.closed)
        self.assertNotIn('SECRET',str(result))
    def test_connection_failure_redacted(self):
        result=inspect_schema(lambda: (_ for _ in ()).throw(RuntimeError('SECRET_DB_PASSWORD')))
        self.assertNotIn('SECRET',str(result)); self.assertFalse(result['schema_compatible'])

if __name__=='__main__': unittest.main()
