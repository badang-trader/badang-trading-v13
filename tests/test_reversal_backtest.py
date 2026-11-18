import unittest
from unittest.mock import patch
from badang_reversal_backtest import reversal_signals,replay

def bars(n=12):
    return [(i*1000,100.,105.,95.,100.,10.) for i in range(n)]

def candidate(at=2,confirm=4,side='BULLISH'):
    return {'available_at_bar':at,'confirmed_at_bar':confirm,
            'invalidation_price':90. if side=='BULLISH' else 110.,
            'direction':side,'invalidated_at_bar':None}

class ReversalBacktestTests(unittest.TestCase):
    def test_no_future_confirmed_signal(self):
        with patch('badang_reversal_backtest.reversal_candidates',return_value=[candidate()]):
            early=reversal_signals(bars(),'EARLY')
            confirmed=reversal_signals(bars(),'CONFIRMED')
        self.assertEqual(early[0]['bar'],2)
        self.assertEqual(confirmed[0]['bar'],4)
        self.assertEqual(confirmed[0]['entry_bar'] if 'entry_bar' in confirmed[0] else confirmed[0]['bar']+1,5)
    def test_stop_first_and_cost(self):
        rows=bars()
        rows[3]=(3000,100.,125.,85.,100.,10.)
        with patch('badang_reversal_backtest.reversal_candidates',return_value=[candidate()]):
            result=replay(rows,'EARLY')
        self.assertEqual(result['trades'][0]['exit_reason'],'STOP')
        self.assertAlmostEqual(result['trades'][0]['net_return'],-0.1518)
    def test_censored(self):
        with patch('badang_reversal_backtest.reversal_candidates',return_value=[candidate(at=9,confirm=None)]):
            result=replay(bars(),'EARLY')
        self.assertEqual(result['summary']['HOLDOUT_LONG']['censored'],1)
        self.assertIsNone(result['summary']['HOLDOUT_LONG']['win_rate'])
    def test_invalid_kind(self):
        with self.assertRaises(ValueError):reversal_signals(bars(),'UNKNOWN')

if __name__=='__main__':unittest.main()
