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
        r=score_historical_prefixes(self.rows,self.rows,self.rows,'scalp',setup_frame='15m',lower_frame='15m',higher_frame='15m')
        self.assertEqual(r['status'],'HISTORICAL_FLOW_MISSING')
        self.assertIsNone(r['signal'])
    def test_unverified_flow_rejected(self):
        r=score_historical_prefixes(self.rows,self.rows,self.rows,'scalp',{'state':'BUY','source':'PROXY'},setup_frame='15m',lower_frame='15m',higher_frame='15m')
        self.assertEqual(r['status'],'HISTORICAL_FLOW_MISSING')
    def test_future_higher_timeframe_bar_rejected(self):
        r=score_historical_prefixes(self.rows,self.rows,self.rows,'scalp',
                                    setup_frame='15m',lower_frame='15m',higher_frame='1H')
        self.assertEqual(r['status'],'FUTURE_TIMEFRAME_BAR_REJECTED')
    def test_neutral_observed_flow_does_not_emit_signal(self):
        r=score_historical_prefixes(
            self.rows,self.rows,self.rows,'scalp',
            {'state':'NEUTRAL','source':'HISTORICAL_OBSERVED'},
            setup_frame='15m',lower_frame='15m',higher_frame='15m')
        self.assertEqual(r['status'],'WAIT_HISTORICAL_CONDITIONS_NOT_MET')
        self.assertIsNone(r['signal'])
    def test_opposite_flow_does_not_emit_signal(self):
        r=score_historical_prefixes(
            self.rows,self.rows,self.rows,'scalp',
            {'state':'SELL','source':'HISTORICAL_OBSERVED'},
            setup_frame='15m',lower_frame='15m',higher_frame='15m')
        self.assertIsNone(r['signal'])
    def test_missing_timeframe_metadata_rejected(self):
        r=score_historical_prefixes(self.rows,self.rows,self.rows,'scalp')
        self.assertEqual(r['status'],'TIMEFRAME_PROVENANCE_MISSING')
if __name__=='__main__':unittest.main()
