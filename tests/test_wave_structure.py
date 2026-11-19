"""Pure wave-structure regression checks with synthetic closed candles."""
import unittest
from badang_decision_427 import closed_bars, structure_review, decision_review, FRAME_MS

def candles(tf='15m', count=80):
    step=FRAME_MS[tf]
    out=[]
    for i in range(count):
        close=100 + i*.08 + (i%8-4)*.12
        out.append([1700000000000//step*step+i*step,close-.05,close+.4,close-.4,close,1000+i])
    return out

class WaveStructureTests(unittest.TestCase):
    def test_last_forming_candle_excluded(self):
        rows=candles()
        rows[-1][4]=rows[-1][1]+.1
        result=structure_review(rows,'15m')
        self.assertEqual(result['status'],'OK')
        self.assertEqual(result['last_closed_time'],rows[-2][0])
        self.assertNotEqual(result['last_closed_price'],rows[-1][4])

    def test_rejects_malformed_unconfirmed_candle(self):
        rows=candles()
        rows[-1][4]=999999
        result=structure_review(rows,'15m')
        self.assertEqual(result['status'],'UNAVAILABLE')
        self.assertIn('마지막 미확정봉',result['reason'])

    def test_missing_timeframe_and_bad_interval(self):
        rows=candles()
        rows[20][0]+=1000
        self.assertEqual(structure_review(rows,'15m')['status'],'UNAVAILABLE')

    def test_invalid_ohlc(self):
        rows=candles()
        rows[10][2]=rows[10][3]-1
        self.assertEqual(structure_review(rows,'15m')['status'],'UNAVAILABLE')

    def test_mode_required_timeframes(self):
        item={'decision_plan_425':{'side':'LONG','score':90,'state':'READY_REVIEW','rr1_net_estimate':2}}
        structures={tf:{'status':'OK'} for tf in ('15m','30m','1H')}
        scalp=decision_review(item,structures,'scalp')
        swing=decision_review(item,structures,'swing')
        self.assertNotIn('15m 확정봉·구조 검증 불가',scalp['reasons'])
        self.assertIn('4H 확정봉·구조 검증 불가',swing['reasons'])
        self.assertIn('1D 확정봉·구조 검증 불가',swing['reasons'])

if __name__=='__main__':
    unittest.main()
