import unittest
from badang_portfolio_research import simulate
from badang_synchronized_equity import synchronized_marks

class PortfolioEquityParity(unittest.TestCase):
    def test_same_trades_same_realized_cash(self):
        rows=[[i*900000,100,102,98,100,1] for i in range(12)]
        cases=[]
        for sym in ('BTC','ETH'):
            trades=[{'partition':'HOLDOUT','net_return':-.1,'signal_bar':0,
                     'entry_bar':1,'exit_bar':5,'entry':100.,'side':'LONG'},
                    {'partition':'HOLDOUT','net_return':.2,'signal_bar':1,
                     'entry_bar':2,'exit_bar':7,'entry':100.,'side':'SHORT'}]
            cases.append({'symbol':sym,'timeframe':'15m','reversal_backtest':{
                'early':{'trades':trades}}})
        histories={(sym,'15m'):rows for sym in ('BTC','ETH')}
        for cap in (.1,.3):
            a=simulate(cases,histories,margin_fraction=.1,
                       max_total_margin_fraction=cap)
            b=synchronized_marks(cases,histories,margin_fraction=.1,
                                 max_total_margin_fraction=cap)
            self.assertEqual(a['accepted'],b['accepted'])
            self.assertEqual(a['rejected_insufficient_margin'],
                             b['rejected_insufficient_margin'])
            self.assertAlmostEqual(a['ending_capital'],b['ending_realized_cash'])
            self.assertAlmostEqual(a['realized_event_drawdown'],
                                   b['realized_event_drawdown'])
    def test_exit_same_timestamp_does_not_fund_entry(self):
        from badang_portfolio_events import allocate
        t={'net_return':0}
        events=[{'entry_ts':0,'exit_ts':10,'key':('BTC','15m'),'t':t},
                {'entry_ts':10,'exit_ts':20,'key':('ETH','15m'),'t':t}]
        accepted,rejected=allocate(events,1000,.5,2,.5)
        self.assertEqual((len(accepted),rejected),(1,1))

if __name__=='__main__':unittest.main()
