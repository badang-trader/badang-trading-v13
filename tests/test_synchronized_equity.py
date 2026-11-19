import unittest
from badang_synchronized_equity import synchronized_marks

class SynchronizedEquityTests(unittest.TestCase):
    def test_two_simultaneous_positions_exact_close(self):
        rows=[[i*900000,100,101,90 if i==1 else 99,90 if i==1 else 100,1] for i in range(6)]
        cases=[]
        for sym,side in [('BTC','LONG'),('ETH','SHORT')]:
            t={'partition':'HOLDOUT','net_return':0.0,'signal_bar':0,
               'entry_bar':0,'exit_bar':4,'entry':100.,'side':side}
            cases.append({'symbol':sym,'timeframe':'15m',
                          'reversal_backtest':{'early':{'trades':[t]}}})
        histories={(s,'15m'):rows for s in ('BTC','ETH')}
        r=synchronized_marks(cases,histories,margin_fraction=.1,
                             max_total_margin_fraction=.2,leverage=2)
        self.assertEqual(r['accepted'],2)
        self.assertEqual(r['complete_close_observations'],4)
        self.assertEqual(r['observations'][0]['open_positions'],2)
        # Equal and opposite directions cancel the same price change.
        self.assertAlmostEqual(r['observations'][0]['unrealized_pnl'],0)
        self.assertAlmostEqual(r['observations'][0]['reserved_margin'],2000)
        self.assertFalse('LIQUIDATION_VERIFIED' in r['risk_warnings'])
    def test_missing_exact_close_not_interpolated(self):
        rows=[[i*900000,100,101,99,100,1] for i in range(6)]
        slow=[[i*1800000,100,101,99,100,1] for i in range(3)]
        cases=[]
        for sym,tf in [('BTC','15m'),('ETH','30m')]:
            t={'partition':'HOLDOUT','net_return':0,'signal_bar':0,
               'entry_bar':0,'exit_bar':2,'entry':100,'side':'LONG'}
            cases.append({'symbol':sym,'timeframe':tf,
                          'reversal_backtest':{'early':{'trades':[t]}}})
        r=synchronized_marks(cases,{('BTC','15m'):rows,('ETH','30m'):slow})
        self.assertGreater(r['skipped_incomplete_mark_timestamps'],0)
        self.assertEqual(r['risk_warnings'][4],'MISSING_MARK_TIMESTAMPS_SKIPPED')
        self.assertGreater(r['missing_by_timeframe'].get('30m',0),0)
        self.assertGreater(r['missing_position_marks'],0)
        self.assertLess(r['complete_timestamp_coverage'],1.0)
        self.assertEqual(sum(r['missing_by_timeframe'].values()),r['missing_position_marks'])

if __name__=='__main__':unittest.main()
