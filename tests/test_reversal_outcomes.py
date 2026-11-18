import unittest
from badang_reversal_outcomes import evaluate_reversal_candidates

class OutcomeTests(unittest.TestCase):
    def rows(self,hl):
        return [(i*1000,100,h,l,100,1) for i,(h,l) in enumerate(hl)]
    def candidate(self,side='BULLISH'):
        return {'direction':side,'available_at_bar':1,
            'confirmation_level':110 if side=='BULLISH' else 90,
            'invalidation_price':90 if side=='BULLISH' else 110}
    def test_future_not_visible_before_availability(self):
        rows=self.rows([(100,100),(101,99),(111,99),(111,89)])
        result=evaluate_reversal_candidates(rows,[self.candidate()],horizon=1)
        self.assertEqual(result['events'][0]['status'],'STRUCTURE_LEVEL_TOUCHED')
        self.assertEqual(result['events'][0]['event_bar'],2)
    def test_ambiguous_intrabar(self):
        rows=self.rows([(100,100),(101,99),(111,89)])
        result=evaluate_reversal_candidates(rows,[self.candidate()])
        self.assertEqual(result['events'][0]['status'],'AMBIGUOUS_SAME_BAR')
    def test_invalidation(self):
        rows=self.rows([(100,100),(101,99),(105,89)])
        result=evaluate_reversal_candidates(rows,[self.candidate()])
        self.assertEqual(result['events'][0]['status'],'INVALIDATED')
    def test_no_trades_claimed(self):
        rows=self.rows([(100,100),(101,99)])
        result=evaluate_reversal_candidates(rows,[self.candidate()])
        self.assertEqual(result['events'][0]['trading_pnl'],'NOT_EVALUATED')
        self.assertFalse(result['events'][0]['horizon_complete'])

if __name__=='__main__':unittest.main()
