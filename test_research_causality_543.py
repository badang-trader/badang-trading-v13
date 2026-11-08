"""Causal checks: a past research signal cannot depend on candles after its decision time."""
import unittest
from badang_analysis_v13 import pivots, rsi, divergence_details, normalize

class ResearchCausalityTests(unittest.TestCase):
    def setUp(self):
        self.rows=[]
        for i in range(270):
            center=100+i*0.03+2.5*((i%17)-8)/8
            self.rows.append({"open":center,"high":center+1.2,"low":center-1.2,
                              "close":center+0.2,"volume":100+i})
    def test_pivots_unchanged_after_future_candles(self):
        for cutoff in (205,220,250):
            past=pivots(self.rows[:cutoff],radius=3)
            future=pivots(self.rows,radius=3)
            # A pivot requires three subsequent completed bars for confirmation.
            confirmed=[p for p in future if p[0]<cutoff-3]
            self.assertEqual(past,confirmed)
    def test_divergence_does_not_read_future_rsi(self):
        for cutoff in (205,235):
            closes=[r["close"] for r in self.rows[:cutoff]]
            past_rsi=rsi(closes)
            past_points=pivots(self.rows[:cutoff])
            baseline=divergence_details(past_points,past_rsi,cutoff)
            future_rsi=rsi([r["close"] for r in self.rows])
            self.assertEqual(baseline,divergence_details(past_points,future_rsi[:cutoff],cutoff))
    def test_normalize_does_not_mutate_input(self):
        before=[dict(r) for r in self.rows]
        normalize(self.rows)
        self.assertEqual(self.rows,before)

if __name__=="__main__":unittest.main()
