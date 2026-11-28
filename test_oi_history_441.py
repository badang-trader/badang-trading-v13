import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from badang_oi_history_441 import record_oi, oi_changes, observe_bitget_oi

class OIHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'oi.db'
        self.now=int(time.time()*1000)

    def test_empty(self):
        self.assertEqual(oi_changes(self.db,'BTCUSDT')['status'],'INSUFFICIENT_HISTORY')

    def test_two_windows(self):
        for t,oi in [(self.now-3600000,100),(self.now-900000,110),(self.now,121)]:
            record_oi(self.db,'BTCUSDT',oi,t)
        v=oi_changes(self.db,'BTCUSDT',self.now)
        self.assertEqual(v['status'],'HISTORY_AVAILABLE')
        self.assertEqual(v['oi_change_15m_pct'],10)
        self.assertEqual(v['oi_change_1h_pct'],21)

    def test_missing_window_not_fabricated(self):
        record_oi(self.db,'BTCUSDT',100,self.now-900000)
        record_oi(self.db,'BTCUSDT',110,self.now)
        v=oi_changes(self.db,'BTCUSDT',self.now)
        self.assertEqual(v['status'],'PARTIAL_HISTORY')
        self.assertIsNone(v['oi_change_1h_pct'])

    def test_other_symbol_excluded(self):
        record_oi(self.db,'ETHUSDT',100,self.now-900000)
        record_oi(self.db,'BTCUSDT',110,self.now)
        self.assertIsNone(oi_changes(self.db,'BTCUSDT',self.now)['oi_change_15m_pct'])

    def test_cross_exchange_rejected(self):
        with self.assertRaises(ValueError): record_oi(self.db,'BTCUSDT',100,self.now,'okx')

    def test_bad_values_rejected(self):
        for v in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): record_oi(self.db,'BTCUSDT',v,self.now)

    def test_stale(self):
        record_oi(self.db,'BTCUSDT',100,self.now-500000)
        self.assertEqual(oi_changes(self.db,'BTCUSDT',self.now)['status'],'STALE_OR_MISSING_CURRENT')

    def test_fetch_on_demand(self):
        with patch('bitget_market_data._get',return_value={'openInterestList':[{'size':'123'}]}):
            v=observe_bitget_oi(self.db,'BTCUSDT')
        self.assertEqual(v['current_oi'],123)
        self.assertEqual(v['collection'],'ON_DEMAND')

if __name__=='__main__': unittest.main()
