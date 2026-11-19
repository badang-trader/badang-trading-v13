"""Regression tests for research-only outcome accounting, not trading performance."""
import unittest
from badang_bitget_technical_experiment import run_experiment,closed_prefix,technical_only_signal

class ResearchAccountingTests(unittest.TestCase):
    def test_closed_prefix_excludes_unclosed_higher_bar(self):
        rows=[[0,100,101,99,100,10],[3600000,101,102,100,101,10]]
        self.assertEqual(len(closed_prefix(rows,'1H',3600000)),1)
        self.assertEqual(len(closed_prefix(rows,'1H',7199999)),1)
        self.assertEqual(len(closed_prefix(rows,'1H',7200000)),2)

    def test_no_trade_without_full_history(self):
        rows=[[i*900000,100,101,99,100,10] for i in range(10)]
        frames={'15m':rows,'30m':rows,'1H':rows}
        result=run_experiment(frames,'scalp')
        self.assertEqual(result['train']['trades'],0)
        self.assertIsNone(result['holdout']['win_rate'])
        self.assertIsNone(result['holdout']['compounded_net_return'])

    def test_no_technical_signal_without_history(self):
        self.assertIsNone(technical_only_signal([],[],[],'scalp'))

if __name__=='__main__':
    unittest.main()
