"""Regression: closed-bar reversal signals must be invariant to unseen future candles.

No live orders or market requests. The deterministic fixture checks the
same historical signal against every growing data prefix.
"""
import unittest
from badang_reversal_backtest import reversal_signals
from badang_reversal_research import reversal_candidates

def fixture():
    # Every OHLCV row is a completed bar; deliberately vary highs and lows.
    closes=[100,102,105,103,99,96,98,102,99,94,92,95,99,101,97,91,89,93,98,104,
            100,95,90,87,92,98,105,101,96,91,88,94,100,108,103,97,92,90,95,102]
    return [[i*900000,float(v),float(v+1),float(v-1),float(v),1.] for i,v in enumerate(closes)]

class CausalPrefixTests(unittest.TestCase):
    def test_early_signals_not_repainted_by_future_bars(self):
        rows=fixture()
        for end in range(12,len(rows)+1):
            earlier=reversal_signals(rows[:end],'EARLY')
            later=[s for s in reversal_signals(rows,'EARLY') if s['bar']<end-1]
            # A signal on the final closed bar of a prefix cannot yet be entered.
            self.assertEqual([(s['bar'],s['side'],s['stop']) for s in earlier],
                             [(s['bar'],s['side'],s['stop']) for s in later],
                             'prefix='+str(end))
    def test_confirmed_signals_not_repainted_by_future_bars(self):
        rows=fixture()
        for end in range(12,len(rows)+1):
            earlier=reversal_signals(rows[:end],'CONFIRMED')
            later=[s for s in reversal_signals(rows,'CONFIRMED') if s['bar']<end-1]
            self.assertEqual([(s['bar'],s['side'],s['stop']) for s in earlier],
                             [(s['bar'],s['side'],s['stop']) for s in later],
                             'prefix='+str(end))
    def test_pivot_availability_not_backdated(self):
        rows=fixture()
        for c in reversal_candidates(rows):
            self.assertGreaterEqual(c['available_at_bar'],c['pivot_bar']+3)
            if c['confirmed_at_bar'] is not None:
                self.assertGreater(c['confirmed_at_bar'],c['available_at_bar'])

if __name__=='__main__':unittest.main()
