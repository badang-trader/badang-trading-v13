import unittest
from badang_db_preflight_473 import preflight, TABLES

class Cursor:
    def __init__(self, present=None, fail=False):
        self.present = present or {}; self.fail = fail; self.queries = []; self.last = None
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if self.fail: raise RuntimeError('SECRET_CONNECTION_DETAILS')
        if sql == 'SELECT 1': self.last = (1,)
        else: self.last = (self.present.get(params[0].removeprefix('public.'), False),)
    def fetchone(self): return self.last
class Connection:
    def __init__(self, cursor): self.c = cursor; self.closed = False
    def cursor(self): return self.c
    def close(self): self.closed = True
class PreflightTests(unittest.TestCase):
    def test_ready(self):
        c=Cursor({name:True for name in TABLES}); con=Connection(c)
        result=preflight(lambda: con)
        self.assertTrue(result['schema_ready']); self.assertFalse(result['trading_ready'])
        self.assertTrue(con.closed)
        self.assertEqual(len(c.queries),4)
        self.assertTrue(all(q.startswith('SELECT ') for q,_ in c.queries))
    def test_missing_table(self):
        result=preflight(lambda:Connection(Cursor({TABLES[0]:True})))
        self.assertTrue(result['database_reachable']); self.assertFalse(result['schema_ready'])
        self.assertFalse(result['tables_present'][TABLES[1]])
    def test_connection_failure_redacts(self):
        result=preflight(lambda: (_ for _ in ()).throw(RuntimeError('SECRET_CONNECTION_DETAILS')))
        self.assertFalse(result['database_reachable'])
        self.assertNotIn('SECRET',str(result))
    def test_query_failure_redacts_and_closes(self):
        con=Connection(Cursor(fail=True)); result=preflight(lambda:con)
        self.assertFalse(result['schema_ready']); self.assertTrue(con.closed)
        self.assertNotIn('SECRET',str(result))
if __name__ == '__main__': unittest.main()
