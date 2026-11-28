import unittest
from unittest.mock import patch, MagicMock
import badang_oi_postgres_443 as m

class TestOI443(unittest.TestCase):
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError): m.record('BTC-USD', 100)
    def test_invalid_oi(self):
        with self.assertRaises(ValueError): m.record('BTCUSDT', float('nan'))
    def test_empty_db_status(self):
        con=MagicMock()
        con.cursor.return_value.__enter__.return_value.fetchall.return_value=[]
        with patch.object(m,'_connection',return_value=con):
            self.assertEqual(m.changes('BTCUSDT')['status'],'STALE_OR_MISSING_CURRENT')
    def test_oi_change(self):
        now=1794000000000
        rows=[(now,110.),(now-900000,100.),(now-3600000,100.)]
        con=MagicMock()
        con.cursor.return_value.__enter__.return_value.fetchall.return_value=rows
        with patch.object(m,'_connection',return_value=con):
            r=m.changes('BTCUSDT',now_ms=now)
        self.assertEqual(r['status'],'HISTORY_AVAILABLE')
        self.assertEqual(r['oi_change_15m_pct'],10.)
        self.assertEqual(r['oi_change_1h_pct'],10.)

if __name__=='__main__': unittest.main()
