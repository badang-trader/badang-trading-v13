"""Regime sample warnings cannot use whole-series bars as regime exposure."""
import unittest
from badang_research_regime_sample_563 import regime_sample_review

class RegimeSampleTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"close":100} for _ in range(1100)]
    def test_sparse_regime_has_trade_warning(self):
        trades=[{"signal_index":25,"entry_index":26,"exit_index":29,"net_return":.1}]
        result=regime_sample_review(self.bars,trades)
        self.assertIn("INSUFFICIENT_COMPLETED_TRADES",result["sideways"]["warnings"])
    def test_whole_series_not_misrepresented_as_regime_exposure(self):
        trades=[{"signal_index":25,"entry_index":26,"exit_index":29,"net_return":.1}]
        result=regime_sample_review(self.bars,trades)
        self.assertFalse(result["sideways"]["regime_specific_bars_measured"])
        self.assertIn("REGIME_EXPOSURE_NOT_MEASURED",result["sideways"]["warnings"])
        self.assertFalse(result["sideways"]["sample_adequate_for_preliminary_review"])
    def test_empty_groups_never_verified(self):
        result=regime_sample_review(self.bars,[])
        self.assertTrue(all(not v["profitability_verified"] for v in result.values()))
    def test_invalid_trade_rejected(self):
        with self.assertRaises(ValueError):
            regime_sample_review(self.bars,[{"signal_index":25,"entry_index":27,"exit_index":29,"net_return":.1}])
if __name__=="__main__":unittest.main()
