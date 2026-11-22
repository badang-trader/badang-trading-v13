import unittest
from badang_censored_position_diagnostic import audit_censored

class CensoredValuationTests(unittest.TestCase):
    def test_unrealized_only_and_no_future_close(self):
        rows=[[i*900000,100,110,90,100+i*2,1] for i in range(4)]
        t={'entry_bar':1,'exit_bar':2,'entry':100,'side':'LONG',
           'net_return':None,'exit_reason':'END_OF_DATA','partition':'HOLDOUT'}
        cases=[{'symbol':'BTC','timeframe':'15m',
                'reversal_backtest':{'early':{'trades':[t]},
                                     'confirmed':{'trades':[]}}}]
        r=audit_censored(cases,{('BTC','15m'):rows})
        self.assertEqual(r['count'],1)
        p=r['positions'][0]
        self.assertEqual(p['last_closed_price'],104)
        self.assertAlmostEqual(p['gross_unrealized_return'],.04)
        self.assertAlmostEqual(p['net_of_entry_cost_proxy'],.0391)
        self.assertTrue(p['not_realized'])
        self.assertTrue(p['not_allocated_to_portfolio'])
    def test_rejects_invented_exit(self):
        rows=[[0,100,101,99,100,1]]
        t={'entry_bar':0,'exit_bar':0,'entry':100,'side':'LONG',
           'net_return':None,'exit_reason':'TARGET','partition':'HOLDOUT'}
        cases=[{'symbol':'BTC','timeframe':'15m',
                'reversal_backtest':{'early':{'trades':[t]},
                                     'confirmed':{'trades':[]}}}]
        with self.assertRaisesRegex(ValueError,'unexpected censored'):
            audit_censored(cases,{('BTC','15m'):rows})

if __name__=='__main__':unittest.main()
