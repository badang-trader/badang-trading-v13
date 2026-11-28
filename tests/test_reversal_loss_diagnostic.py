import unittest
from badang_reversal_loss_diagnostic import summarize_loss_reasons

class LossDiagnosticTests(unittest.TestCase):
    def test_excludes_censored_from_profitability(self):
        trades=[
            {'partition':'TRAIN','net_return':-0.02,'exit_reason':'STOP','entry':100.,'stop':99.},
            {'partition':'TRAIN','net_return':None,'exit_reason':'END_OF_PARTITION','entry':100.,'stop':99.},
            {'partition':'HOLDOUT','net_return':0.04,'exit_reason':'TARGET','entry':100.,'stop':97.}]
        cases=[{'reversal_backtest':{kind:{'trades':trades} for kind in ('early','confirmed')}}]
        result=summarize_loss_reasons(cases)['strategy_loss_attribution']['early']
        self.assertEqual(result['TRAIN']['completed'],1)
        self.assertEqual(result['TRAIN']['censored'],1)
        self.assertEqual(result['TRAIN']['stops'],1)
        self.assertEqual(result['TRAIN']['entry_to_stop_distance_buckets']['FROM_0_5_TO_2_PCT']['completed'],1)
        self.assertEqual(result['TRAIN']['entry_to_stop_distance_buckets']['AT_LEAST_2_PCT']['completed'],0)
        self.assertEqual(result['TRAIN']['mean_net_return'],-0.02)
        self.assertEqual(result['HOLDOUT']['targets'],1)

if __name__=='__main__':unittest.main()
