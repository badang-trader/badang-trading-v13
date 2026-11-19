import unittest
from badang_reversal_causal_context import signal_context,diagnose

def candles(n=45):
    return [[i*900000,100.+i*.1,101.+i*.1,99.+i*.1,100.+i*.1,1.] for i in range(n)]

class CausalContextTests(unittest.TestCase):
    def test_prefix_invariant(self):
        rows=candles()
        a=signal_context(rows[:30],25,'LONG',103.,99.)
        b=signal_context(rows,25,'LONG',103.,99.)
        self.assertEqual(a,b)
    def test_requires_20_closed_candles(self):
        self.assertIsNone(signal_context(candles(),19,'LONG',103.,99.))
    def test_censored_excluded_and_small_samples_marked(self):
        rows=candles()
        case={'symbol':'BTC','timeframe':'15m','reversal_backtest':{
            'early':{'trades':[{'partition':'TRAIN','signal_bar':25,'side':'LONG',
                'entry':103.,'stop':101.,'net_return':-.02,'exit_reason':'STOP'},
                {'partition':'TRAIN','signal_bar':27,'side':'LONG','entry':103.,
                 'stop':101.,'net_return':None,'exit_reason':'END_OF_PARTITION'}]},
            'confirmed':{'trades':[]}}}
        output=diagnose([case],{('BTC','15m'):rows})
        groups=output['groups']
        self.assertTrue(groups)
        self.assertTrue(all(g['completed']==1 and g['small_sample'] for g in groups))
        self.assertTrue(all(g['stops']==1 for g in groups))

if __name__=='__main__':unittest.main()
