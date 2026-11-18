import unittest
from unittest.mock import patch
from badang_elliott_research import wave_scenarios, abc_scenarios

class WaveResearchTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(wave_scenarios([]),[])
    def test_candidate_availability_and_fibonacci(self):
        prices=[100,110,105,125,115,130]
        pivots=[{'type':'LOW' if i%2==0 else 'HIGH','price':p,
                 'pivot_bar':i+2,'confirmed_at_bar':i+3} for i,p in enumerate(prices)]
        rows=[(i*1000,100,140,90,100,1) for i in range(15)]
        with patch('badang_elliott_research.confirmed_pivots',return_value=pivots):
            result=wave_scenarios(rows)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['available_at_bar'],8)
        self.assertEqual(result[0]['status'],'UNVALIDATED_IMPULSE_GEOMETRY')
        self.assertFalse(result[0]['live_signal_eligible'])
        self.assertEqual(result[0]['wave_degree'],'UNVERIFIED')
        self.assertLess(result[0]['retracement_618'],result[0]['retracement_382'])
        self.assertIsNone(result[0]['invalidation_price'])
        self.assertEqual(result[0]['terminal_reference_price'],130)
        self.assertEqual(result[0]['invalidation_status'],'NOT_VALIDATED_FOR_WAVE_DEGREE')
    def test_abc_separate_from_impulse_and_causal(self):
        prices=[110,90,100,75]
        pivots=[{'type':'HIGH' if i%2==0 else 'LOW','price':p,
                 'pivot_bar':i+2,'confirmed_at_bar':i+3} for i,p in enumerate(prices)]
        rows=[(i*1000,100,140,60,100,1) for i in range(12)]
        with patch('badang_elliott_research.confirmed_pivots',return_value=pivots):
            abc=abc_scenarios(rows)
            impulse=wave_scenarios(rows)
        self.assertEqual(len(abc),1)
        self.assertEqual(abc[0]['available_at_bar'],6)
        self.assertEqual(abc[0]['scenario'],'POSSIBLE_ABC_ZIGZAG_END')
        self.assertIsNone(abc[0]['invalidation_price'])
        self.assertEqual(abc[0]['terminal_reference_price'],75)
        self.assertEqual(impulse,[])
    def test_reject_future_pivot_confirmation(self):
        rows=[(i*1000,100,140,90,100,1) for i in range(10)]
        pivots=[{'type':'LOW','price':100,'pivot_bar':5,'confirmed_at_bar':10}]
        with patch('badang_elliott_research.confirmed_pivots',return_value=pivots):
            with self.assertRaisesRegex(ValueError,'outside available closed bars'):
                wave_scenarios(rows)
    def test_reject_out_of_order_confirmations(self):
        rows=[(i*1000,100,140,90,100,1) for i in range(10)]
        pivots=[{'type':'LOW','price':100,'pivot_bar':2,'confirmed_at_bar':6},
                {'type':'HIGH','price':110,'pivot_bar':3,'confirmed_at_bar':5}]
        with patch('badang_elliott_research.confirmed_pivots',return_value=pivots):
            with self.assertRaisesRegex(ValueError,'not chronological'):
                abc_scenarios(rows)
    def test_reject_wave_three_shortest(self):
        prices=[100,110,105,110.5,110.2,130]
        pivots=[{'type':'LOW' if i%2==0 else 'HIGH','price':p,
                 'pivot_bar':i+2,'confirmed_at_bar':i+3} for i,p in enumerate(prices)]
        rows=[(i*1000,100,140,90,100,1) for i in range(15)]
        with patch('badang_elliott_research.confirmed_pivots',return_value=pivots):
            self.assertEqual(wave_scenarios(rows),[])

if __name__=='__main__':unittest.main()
