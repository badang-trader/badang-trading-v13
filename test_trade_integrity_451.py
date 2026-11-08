import unittest
from badang_trade_sample_450 import parse_fills
NOW=1794000000000
class TradeIntegrityTests(unittest.TestCase):
    def test_recent_ids(self):
        r=parse_fills([{'side':'buy','size':'1','ts':NOW-1000,'tradeId':'x'}],'BTCUSDT',NOW)
        self.assertEqual(r['sample_freshness'],'RECENT')
        self.assertEqual(r['sample_id_integrity'],'IDS_PRESENT')
        self.assertFalse(r['is_cvd'])
    def test_stale(self):
        r=parse_fills([{'side':'sell','size':'1','ts':NOW-200000}],'BTCUSDT',NOW)
        self.assertEqual(r['sample_freshness'],'STALE')
        self.assertEqual(r['sample_id_integrity'],'UNVERIFIABLE_IDS')
    def test_oversized(self):
        with self.assertRaises(ValueError):
            parse_fills([{}]*101,'BTCUSDT',NOW)
if __name__=='__main__': unittest.main()
