import unittest
from badang_integrated_432 import build_report

def frame(px=100, direction='UP', **quality):
    em=(95,90,85) if direction=='UP' else (105,110,115)
    return {'analysis_status':'VALID','quality':{'usable':True,'gaps':0,'closed_count':319,**quality},'ema20':em[0],'ema50':em[1],'ema200':em[2],'current_price':px,'atr14':2,'levels':{'supports':[{'price':98,'touches':2}],'resistances':[{'price':102,'touches':2}]}}
class QualityGate(unittest.TestCase):
    def test_empty_cannot_claim_trend(self):
        r=build_report({'timeframes':{}})
        self.assertEqual(r['data_coverage'],'INSUFFICIENT')
        self.assertIn('보류',r['signal'])
        self.assertFalse(r['key_supports'])
    def test_single_frame_insufficient(self):
        r=build_report({'timeframes':{'15m':frame()}})
        self.assertEqual(r['data_coverage'],'INSUFFICIENT')
    def test_all_valid(self):
        r=build_report({'timeframes':{tf:frame() for tf in ('15m','30m','1H','4H')}})
        self.assertEqual(r['data_coverage'],'COMPLETE')
        self.assertEqual(r['trend_reading'],'상승 정렬 우세')
    def test_gaps_excluded(self):
        r=build_report({'timeframes':{'15m':frame(gaps=2),'30m':frame()}})
        self.assertEqual(r['rejected_frames']['15m'],'QUALITY')
    def test_stale_excluded(self):
        r=build_report({'timeframes':{'15m':frame(usable=False),'30m':frame()}})
        self.assertEqual(r['valid_frame_count'],1)
    def test_price_disagreement(self):
        r=build_report({'timeframes':{'15m':frame(100),'30m':frame(110)}})
        self.assertEqual(r['data_coverage'],'INSUFFICIENT')
        self.assertTrue(any('3%' in s for s in r['limitations']))
    def test_partial_is_explicit(self):
        r=build_report({'timeframes':{'15m':frame(),'30m':frame()}})
        self.assertEqual(r['data_coverage'],'PARTIAL')
if __name__=='__main__':unittest.main()
