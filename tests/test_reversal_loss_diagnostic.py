import unittest
from badang_reversal_loss_diagnostic import summarize_loss_reasons

class LossDiagnosticTests(unittest.TestCase):
    def test_excludes_censored_from_profitability(self):
        trades=[
            {'partition':'TRAIN','net_return':-0.02,'exit_reason':'STOP'},
            {'partition':'TRAIN','net_return':None,'exit_reason':'END_OF_PARTITION'},
            {'partition':'HOLDOUT','net_return':0.04,'exit_reason':'TARGET'}]
        cases=[{'reversal_backtest':{kind:{'trades':trades} for kind in ('early','confirmed')}}]
        result=summarize_loss_reasons(cases)['strategy_loss_attribution']['early']
        self.assertEqual(result['TRAIN']['completed'],1)
        self.assertEqual(result['TRAIN']['censored'],1)
        self.assertEqual(result['TRAIN']['stops'],1)
        self.assertEqual(result['TRAIN']['mean_net_return'],-0.02)
        self.assertEqual(result['HOLDOUT']['targets'],1)

if __name__=='__main__':unittest.main()
