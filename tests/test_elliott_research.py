import unittest
from unittest.mock import patch
from badang_elliott_research import wave_scenarios

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
        self.assertLess(result[0]['retracement_618'],result[0]['retracement_382'])
    def test_reject_wave_three_shortest(self):
        prices=[100,110,105,110.5,110.2,130]
        pivots=[{'type':'LOW' if i%2==0 else 'HIGH','price':p,
                 'pivot_bar':i+2,'confirmed_at_bar':i+3} for i,p in enumerate(prices)]
        rows=[(i*1000,100,140,90,100,1) for i in range(15)]
        with patch('badang_elliott_research.confirmed_pivots',return_value=pivots):
            self.assertEqual(wave_scenarios(rows),[])

if __name__=='__main__':unittest.main()
