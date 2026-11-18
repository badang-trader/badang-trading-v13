import unittest
from unittest.mock import patch
from badang_paired_trend_filter import compare

def trade(net,reason='STOP'):
    return {'partition':'HOLDOUT','net_return':net,'signal_bar':2,'side':'LONG','exit_reason':reason}

class PairedFilterTests(unittest.TestCase):
    def test_excluded_trades_not_hidden_and_unknown_separate(self):
        trades=[trade(-.02),trade(.04,'TARGET'),trade(-.03)]
        case={'symbol':'BTC','timeframe':'15m',
              'reversal_backtest':{'early':{'trades':trades},'confirmed':{'trades':[]}}}
        values=iter([{'EMA20':'WITH','EMA50':'INSUFFICIENT_HISTORY','EMA200':'INSUFFICIENT_HISTORY','higher':'NO_HIGHER_FRAME'},
                     {'EMA20':'AGAINST','EMA50':'INSUFFICIENT_HISTORY','EMA200':'INSUFFICIENT_HISTORY','higher':'NO_HIGHER_FRAME'},
                     {'EMA20':'INSUFFICIENT_HISTORY','EMA50':'INSUFFICIENT_HISTORY','EMA200':'INSUFFICIENT_HISTORY','higher':'NO_HIGHER_FRAME'}])
        with patch('badang_paired_trend_filter.alignment',side_effect=lambda *args:next(values)):
            result=compare([case],{})
        r=next(x for x in result['rows'] if x['strategy']=='early' and x['partition']=='HOLDOUT' and x['filter']=='EMA20')
        self.assertEqual((r['completed_opportunities'],r['known_opportunities'],r['unknown_opportunities']),(3,2,1))
        self.assertEqual((r['included']['count'],r['excluded']['count']),(1,1))
        self.assertAlmostEqual(r['baseline_known']['sum_net_trade_returns'],.02)
        self.assertAlmostEqual(r['filtered_return_per_known_opportunity'],-.01)
        self.assertTrue(r['not_portfolio_backtest'])
    def test_empty_group(self):
        case={'symbol':'ETH','timeframe':'1D','reversal_backtest':{'early':{'trades':[]},'confirmed':{'trades':[]}}}
        r=compare([case],{})
        self.assertEqual(len(r['rows']),16)
        self.assertIsNone(r['rows'][0]['filtered_return_per_known_opportunity'])

if __name__=='__main__':unittest.main()
