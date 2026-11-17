"""Wave candidates cannot be known until the final pivot is confirmed."""
import unittest
from badang_analysis_v13 import wave_candidates, analyze
from test_divergence_real_pipeline_514 import bars

class WaveObservableTests(unittest.TestCase):
    def test_four_pivot_abc_confirmation(self):
        points=[(10,"H",120.),(18,"L",100.),(25,"H",112.),(35,"L",90.)]
        results=wave_candidates(points,total_bars=40)
        for w in results:
            self.assertEqual(w["first_observable_bar_index"],38)
            self.assertTrue(w["observable_in_snapshot"])
    def test_candidate_cannot_be_observed_early(self):
        points=[(10,"H",120.),(18,"L",100.),(25,"H",112.),(35,"L",90.)]
        for w in wave_candidates(points,total_bars=37):
            self.assertFalse(w["observable_in_snapshot"])
    def test_metadata_is_consistent(self):
        points=[(10,"H",120.),(18,"L",100.),(25,"H",112.),(35,"L",90.)]
        for w in wave_candidates(points,total_bars=40):
            self.assertEqual(w["first_observable_bar_index"],max(p["bar_index"] for p in w["pivot_points"])+3)
    def test_scanner_output_has_wave_confirmation_metadata(self):
        data=analyze(bars(),symbol="BTC",mode="scalp")
        self.assertEqual(data["status"],"ok")
        for w in data["wave_candidates"]:
            self.assertIn("observable_in_snapshot",w)
            self.assertTrue(w["observable_in_snapshot"])
if __name__=="__main__":
    unittest.main()
