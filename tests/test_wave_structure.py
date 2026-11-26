"""Pure wave-structure regression checks with synthetic closed candles."""
import unittest
from badang_decision_427 import (
    FRAME_MS, annotate_lower_wave_geometry, closed_bars, decision_review,
    historical_wave_shapes, lower_pivot_evidence, structure_review,
)

def candles(tf='15m', count=80):
    step=FRAME_MS[tf]
    out=[]
    for i in range(count):
        close=100 + i*.08 + (i%8-4)*.12
        out.append([1700000000000//step*step+i*step,close-.05,close+.4,close-.4,close,1000+i])
    return out

class WaveStructureTests(unittest.TestCase):
    def test_lower_pivots_use_matching_extrema_and_original_confirmation_cutoff(self):
        step = FRAME_MS['5m']
        points = [(0,108),(30,100),(34,115),(38,109),(42,120),(54,101),(66,122),(78,112)]
        bars = []
        for (left,start), (right,end) in zip(points, points[1:]):
            for i in range(left,right):
                price = start + (end-start)*(i-left)/(right-left)
                bars.append([i*step,price,price+.1,price-.1,price,10])
        shape = {'pattern':'ABC_FLAT_GEOMETRY',
                 'pivot_times':[i*step for i in (30,42,54,66)],
                 'pivot_prices':[bars[i][col] for i,col in ((30,3),(42,2),(54,3),(66,2))],
                 'known_at_ms':75*step,'subdivision_verified':False}
        prefix = lower_pivot_evidence(shape, 3*step, bars[:75], '5m')
        whole = lower_pivot_evidence(shape, 3*step, bars, '5m')
        self.assertEqual(prefix, whole)
        self.assertEqual(whole['leg_turn_counts'], [3,1,1])
        structures = {'15m': {'historical_wave_shapes':[shape]}}
        annotate_lower_wave_geometry(structures, {'5m':{'exchange':'bitget','candles':bars}}, 77*step)
        self.assertEqual(shape['lower_pivot_evidence'], whole)
        self.assertFalse(shape['subdivision_verified'])
        self.assertEqual(lower_pivot_evidence(shape, 3*step, bars[31:], '5m')['status'],
                         'INSUFFICIENT_COVERAGE')
        bars[31][3] = bars[30][3]
        self.assertEqual(lower_pivot_evidence(shape, 3*step, bars, '5m')['status'],
                         'AMBIGUOUS_ENDPOINT')

    def test_abc_keeps_overlapping_shapes_until_subdivisions_are_verified(self):
        step = FRAME_MS['15m']
        for points in ([100, 120, 101, 122], [120, 100, 119, 98]):
            pivots = [{'price': price, 'time': i*step, 'confirmed_at': (i+3)*step}
                      for i,price in enumerate(points)]
            result = historical_wave_shapes(pivots, '15m')
            self.assertEqual([x['pattern'] for x in result],
                             ['ABC_ZIGZAG_GEOMETRY', 'ABC_FLAT_GEOMETRY'])
            self.assertEqual([x['geometry_evidence']['expected_subdivision'] for x in result],
                             [[5, 3, 5], [3, 3, 5]])
            self.assertTrue(all(x['geometry_evidence']['b_retrace'] == .95 for x in result))
            self.assertTrue(all(x['known_at_ms'] == 7*step and not x['used_in_score']
                                and not x['subdivision_verified'] for x in result))

    def test_flat_variants_use_c_endpoint_relative_to_a(self):
        step = FRAME_MS['15m']
        for prices,variant in (([100,120,98,123], 'EXPANDED'), ([100,120,98,118], 'RUNNING')):
            pivots = [{'price': price, 'time': i*step, 'confirmed_at': (i+3)*step}
                      for i,price in enumerate(prices)]
            shape, = historical_wave_shapes(pivots, '15m')
            self.assertEqual(shape['pattern'], 'ABC_FLAT_GEOMETRY')
            self.assertEqual(shape['geometry_evidence']['variant'], variant)
            self.assertFalse(shape['subdivision_verified'])

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
