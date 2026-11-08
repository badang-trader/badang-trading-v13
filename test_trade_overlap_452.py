import unittest
from badang_trade_overlap_452 import audit_pair
T=1_800_000_000_000

def trade(i,ts):
    return {'tradeId':str(i),'symbol':'BTCUSDT','side':'buy','size':'1','ts':str(ts)}

class TestOverlap(unittest.TestCase):
    def test_overlap_is_not_cvd(self):
        r=audit_pair([trade(1,T-3000),trade(2,T-2000)], [trade(2,T-2000),trade(3,T-1000)], 'BTCUSDT', T, T+1000)
        self.assertEqual(r['status'],'OVERLAP_OBSERVED')
        self.assertEqual(r['overlap_count'],1)
        self.assertFalse(r['coverage_confirmed'])
        self.assertFalse(r['is_cvd'])
    def test_no_overlap_unknown_gap(self):
        r=audit_pair([trade(1,T-3000)], [trade(2,T-1000)], 'BTCUSDT', T,T+1000)
        self.assertEqual(r['status'],'NO_OVERLAP_GAP_UNKNOWN')
    def test_missing_id(self):
        x=trade(1,T-2000); x.pop('tradeId')
        r=audit_pair([x],[trade(2,T-1000)],'BTCUSDT',T,T+1000)
        self.assertEqual(r['status'],'MISSING_IDS')
    def test_time_regression(self):
        r=audit_pair([trade(1,T-1000)], [trade(2,T-2000)], 'BTCUSDT',T,T+1000)
        self.assertEqual(r['status'],'TIMESTAMP_REGRESSION')
    def test_collection_order(self):
        with self.assertRaises(ValueError):
            audit_pair([],[],'BTCUSDT',T,T)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            audit_pair([trade(1,T-2000),trade(1,T-1000)],[trade(2,T-1000)],'BTCUSDT',T,T+1000)

if __name__=='__main__': unittest.main()
