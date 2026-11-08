"""Elliott wave candidate invariants: overlap, wave 3 shortest, mirrored direction."""
import unittest
from badang_analysis_v13 import wave_candidates

def points(prices):
    return [(i,"L" if i%2==0 else "H",float(p)) for i,p in enumerate(prices)]

class WaveRulesTests(unittest.TestCase):
    def test_valid_bullish_impulse_candidate(self):
        patterns=wave_candidates(points([100,110,105,125,115,135]))
        self.assertTrue(any(x["pattern"]=="5-wave impulse candidate" and x["direction"]=="up" for x in patterns))
    def test_wave_four_overlapping_wave_one_rejected(self):
        patterns=wave_candidates(points([100,110,105,125,109,135]))
        self.assertFalse(any(x["pattern"]=="5-wave impulse candidate" for x in patterns))
    def test_wave_three_shortest_rejected(self):
        patterns=wave_candidates(points([100,120,115,125,121,145]))
        self.assertFalse(any(x["pattern"]=="5-wave impulse candidate" for x in patterns))
    def test_bearish_impulse_candidate(self):
        patterns=wave_candidates(points([140,130,135,115,125,105]))
        self.assertTrue(any(x["pattern"]=="5-wave impulse candidate" and x["direction"]=="down" for x in patterns))
    def test_wave_two_crosses_origin_rejected(self):
        patterns=wave_candidates(points([100,110,99,125,115,135]))
        self.assertFalse(any(x["pattern"]=="5-wave impulse candidate" for x in patterns))

if __name__=="__main__":unittest.main()
