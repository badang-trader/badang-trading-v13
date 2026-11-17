import unittest
from badang_historical_signal_adapter import analyze_closed_prefix,score_historical_prefixes

class HistoricalSignalAdapterTests(unittest.TestCase):
    def setUp(self):
        self.rows=[[i*900000,100+i*.1,101+i*.1,99+i*.1,100+i*.1,10] for i in range(220)]
    def test_prefix_indicator_calculation(self):
        r=analyze_closed_prefix(self.rows)
        self.assertEqual(r['trend'],'UP')
        self.assertIn('macd',r)
        self.assertGreater(r['atr'],0)
    def test_no_history_no_signal(self):
        self.assertIsNone(analyze_closed_prefix(self.rows[:200]))
    def test_flow_not_invented(self):
        r=score_historical_prefixes(self.rows,self.rows,self.rows,'scalp')
        self.assertEqual(r['status'],'HISTORICAL_FLOW_MISSING')
        self.assertIsNone(r['signal'])
    def test_unverified_flow_rejected(self):
        r=score_historical_prefixes(self.rows,self.rows,self.rows,'scalp',{'state':'BUY','source':'PROXY'})
        self.assertEqual(r['status'],'HISTORICAL_FLOW_MISSING')
if __name__=='__main__':unittest.main()
