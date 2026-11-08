"""Elliott pivot regression: flat plateaus must not fabricate wave structure."""
import unittest
from badang_analysis_v13 import pivots, wave_candidates

def candle(high,low):
    return {"open":(high+low)/2,"high":high,"low":low,"close":(high+low)/2,"volume":10}

class WavePivotTests(unittest.TestCase):
    def test_flat_market_has_no_pivots_or_wave_candidates(self):
        rows=[candle(101,99) for _ in range(45)]
        points=pivots(rows)
        self.assertEqual(points,[])
        self.assertEqual(wave_candidates(points),[])
    def test_equal_high_plateau_does_not_create_high_pivot(self):
        rows=[candle(102,98) for _ in range(30)]
        rows[12]=candle(110,98)
        rows[13]=candle(110,98)
        self.assertFalse(any(t=="H" for _,t,_ in pivots(rows)))
    def test_unique_high_and_low_are_detected(self):
        rows=[candle(102,98) for _ in range(30)]
        rows[9]=candle(110,98)
        rows[20]=candle(102,90)
        points=pivots(rows)
        self.assertIn((9,"H",110),points)
        self.assertIn((20,"L",90),points)

if __name__=="__main__":unittest.main()
