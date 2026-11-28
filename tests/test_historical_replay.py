import unittest
from badang_historical_replay import replay_historical_signals
STEP=900000
class HistoricalReplayTests(unittest.TestCase):
    def setUp(self):
        self.rows=[[i*STEP,100,111,90,100,10] for i in range(6)]
    def test_callback_sees_only_past_prefix(self):
        seen=[]
        def cb(prefix,tf):
            seen.append((len(prefix),prefix[-1][0]))
            return None
        r=replay_historical_signals(self.rows,'15m',asof_ms=6*STEP,signal_fn=cb,warmup_bars=2)
        self.assertEqual(seen,[(2,STEP),(3,2*STEP),(4,3*STEP),(5,4*STEP)])
        self.assertEqual(r['generated_signals'],0)
        self.assertEqual(r['backtest']['status'],'HISTORICAL_SIGNALS_REQUIRED')
    def test_provenance_is_not_claimed_verified(self):
        def cb(prefix,tf):
            return {'side':'LONG','score':82,'stop':95,'target':110}
        r=replay_historical_signals(self.rows,'15m',asof_ms=6*STEP,signal_fn=cb,warmup_bars=2)
        self.assertFalse(r['historical_market_performance_verified'])
        self.assertGreater(r['generated_signals'],0)
        self.assertEqual(r['backtest']['trades'][0]['entry_bar'],2)
    def test_forming_bar_rejected_before_signal(self):
        called=[]
        def cb(prefix,tf):
            called.append(True)
        with self.assertRaisesRegex(ValueError,'forming'):
            replay_historical_signals(self.rows,'15m',asof_ms=5*STEP,signal_fn=cb,warmup_bars=2)
        self.assertFalse(called)
if __name__=='__main__':unittest.main()
