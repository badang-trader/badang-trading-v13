import unittest
from badang_support_decision_map_research import support_decision_map
from unittest.mock import patch

class DecisionMapTests(unittest.TestCase):
    def test_order_and_next_zone(self):
        zones = [dict(lower=90,upper=92,center=91,status='historical_support',
                      evidence_grade='moderate_evidence',evidence_score=65,
                      volume_node='ordinary',invalidated_if='close below lower'),
                 dict(lower=95,upper=97,center=96,status='historical_support',
                      evidence_grade='limited_evidence',evidence_score=40,
                      volume_node='none',invalidated_if='close below lower')]
        with patch('badang_support_decision_map_research.validated_support_reliability',
                   return_value={'status':'ok','zones':zones,'warnings':[]}):
            result=support_decision_map([{'open':100,'high':101,'low':99,'close':100,'volume':10}], 'BTC','1h',exchange_now_ms=7200000)
        self.assertEqual([z['zone_lower'] for z in result['observation_zones']],[95,90])
        self.assertEqual(result['observation_zones'][0]['next_observation_zone']['lower'],90)
        self.assertIsNone(result['observation_zones'][1]['next_observation_zone'])
        self.assertIsNone(result['rebound_probability'])
    def test_broken_support_excluded(self):
        zones = [dict(lower=98, upper=99, status='broken', evidence_grade='invalidated',
                      evidence_score=0, volume_node='none', invalidated_if='broken'),
                 dict(lower=90, upper=92, status='historical_support',
                      evidence_grade='moderate_evidence', evidence_score=65,
                      volume_node='ordinary', invalidated_if='close below lower')]
        with patch('badang_support_decision_map_research.validated_support_reliability',
                   return_value={'status':'ok','zones':zones,'warnings':[]}):
            result=support_decision_map([{'open':100,'high':101,'low':99,'close':100,'volume':10}], 'BTC','1h',exchange_now_ms=7200000)
        self.assertEqual(len(result['observation_zones']),1)
        self.assertEqual(result['observation_zones'][0]['zone_lower'],90)

    def test_no_zone_is_not_a_buy_signal(self):
        with patch('badang_support_decision_map_research.validated_support_reliability',
                   return_value={'status':'ok','zones':[],'warnings':[]}):
            result=support_decision_map([{'open':100,'high':101,'low':99,'close':100,'volume':10}], 'BTC','1h',exchange_now_ms=7200000)
        self.assertEqual(result['observation_zones'],[])
        self.assertFalse(result['trading_ready'])
        self.assertIsNone(result['rebound_probability'])
    def test_missing_clock_rejected(self):
        result=support_decision_map([], 'BTC','1h')
        self.assertEqual(result['status'],'missing_exchange_clock')

    def test_open_candle_rejected(self):
        candles=[{'timestamp':i*3600000,'open':100,'high':101,'low':99,'close':100,'volume':10} for i in range(80)]
        result=support_decision_map(candles,'BTC','1h',exchange_now_ms=79*3600000)
        self.assertEqual(result['status'],'open_or_future_candle')

    def test_missing_bar_rejected(self):
        candles=[{'timestamp':i*3600000,'open':100,'high':101,'low':99,'close':100,'volume':10} for i in range(80) if i!=30]
        result=support_decision_map(candles,'BTC','1h',exchange_now_ms=80*3600000)
        self.assertEqual(result['status'],'noncontiguous_history')

    def test_unconfirmed_is_empty(self):
        result=support_decision_map([], 'BTC','1h',confirmed=False)
        self.assertEqual(result['status'],'unconfirmed')
        self.assertEqual(result['observation_zones'],[])
if __name__=='__main__':unittest.main()

[executed on device: DESKTOP-P1HHLJC (f621e81e-b344-4287-b962-f72b21cec132)]