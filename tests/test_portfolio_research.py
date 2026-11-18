import unittest
from badang_portfolio_research import simulate

def fixture():
    candles=[(i*900000,100,101,99,100,1) for i in range(12)]
    trades=[{'partition':'HOLDOUT','net_return':-.1,'signal_bar':0,'entry_bar':1,
             'exit_bar':5,'side':'LONG'},
            {'partition':'HOLDOUT','net_return':.2,'signal_bar':1,'entry_bar':2,
             'exit_bar':6,'side':'LONG'}]
    case={'symbol':'BTC','timeframe':'15m','reversal_backtest':{
        'early':{'trades':trades},'confirmed':{'trades':[]}}}
    return [case],{('BTC','15m'):candles}

class PortfolioResearchTests(unittest.TestCase):
    def test_capital_and_concurrent_margin(self):
        cases,histories=fixture()
        r=simulate(cases,histories,margin_fraction=.1,leverage=2,max_total_margin_fraction=.1)
        self.assertEqual(r['accepted'],1)
        self.assertEqual(r['rejected_insufficient_margin'],1)
        self.assertAlmostEqual(r['ending_capital'],9800)
        self.assertEqual(r['max_simultaneous_positions'],1)
        self.assertEqual(r['liquidation_risk'],'NOT_MODELED')
    def test_no_position_limit_violation(self):
        cases,histories=fixture()
        r=simulate(cases,histories,margin_fraction=.1,leverage=2,max_total_margin_fraction=.2)
        self.assertEqual(r['accepted'],2)
        self.assertEqual(r['max_simultaneous_positions'],2)
        self.assertAlmostEqual(r['ending_capital'],10200)
    def test_invalid_parameters(self):
        cases,histories=fixture()
        with self.assertRaises(ValueError):
            simulate(cases,histories,initial_capital=0)

if __name__=='__main__':unittest.main()
