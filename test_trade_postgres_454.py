import time
import unittest
from unittest.mock import patch
from badang_trade_postgres_454 import save_snapshot, status

class Cursor:
    def __init__(self, state): self.state=state; self.query=''
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def execute(self,query,args=None):
        self.query=query
        if 'INSERT INTO badang_trade_snapshots' in query:
            self.state['rows'].append((args[1],args[2]))
    def fetchone(self):
        return (self.state['rows'][-1][0],self.state['rows'][-1][1]) if self.state['rows'] else None
    def fetchall(self): return [(r[0],) for r in reversed(self.state['rows'])]
class Connection:
    def __init__(self,state): self.state=state
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def close(self): pass
    def cursor(self): return Cursor(self.state)
class TestTradePG(unittest.TestCase):
    def setUp(self):
        self.state={'rows':[]}
        self.patcher=patch('badang_trade_postgres_454._connection',side_effect=lambda:Connection(self.state))
        self.patcher.start()
        self.now=int(time.time()*1000)
    def tearDown(self): self.patcher.stop()
    def row(self,id,ts): return {'tradeId':str(id),'symbol':'BTCUSDT','side':'buy','size':'1','ts':str(ts)}
    def test_insert_and_status(self):
        result=save_snapshot('BTCUSDT',[self.row(1,self.now-1000)],self.now)
        self.assertFalse(result['is_cvd'])
        self.assertEqual(status('BTCUSDT',self.now)['snapshot_count'],1)
    def test_duplicate_timestamp_rejected(self):
        save_snapshot('BTCUSDT',[self.row(1,self.now-1000)],self.now)
        with self.assertRaises(ValueError): save_snapshot('BTCUSDT',[self.row(2,self.now-1000)],self.now)
    def test_old_collection_rejected(self):
        with self.assertRaises(ValueError): save_snapshot('BTCUSDT',[],self.now-100_000_000)
    def test_future_trade_rejected(self):
        with self.assertRaises(ValueError): save_snapshot('BTCUSDT',[self.row(1,self.now+61_000)],self.now)
    def test_two_snapshots_overlap_not_cvd(self):
        save_snapshot('BTCUSDT',[self.row(1,self.now-1000)],self.now)
        result=save_snapshot('BTCUSDT',[self.row(1,self.now-1000),self.row(2,self.now+1000)],self.now+2000)
        self.assertEqual(result['overlap_audit']['status'],'OVERLAP_OBSERVED')
        self.assertFalse(result['coverage_confirmed'])
if __name__=='__main__': unittest.main()
