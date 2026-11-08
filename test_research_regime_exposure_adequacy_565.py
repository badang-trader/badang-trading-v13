"""Regime exposure and trade-count screening must both pass."""
import unittest
from badang_research_regime_sample_563 import regime_sample_review

class RegimeExposureAdequacyTests(unittest.TestCase):
    def test_large_total_history_cannot_hide_small_regime(self):
        bars=[{"close":100} for _ in range(1200)]
        bars[-1]["close"]=200
        result=regime_sample_review(bars,[],minimum_trades=1,minimum_bars=1000)
        self.assertEqual(result["up"]["regime_bars"],1)
        self.assertIn("INSUFFICIENT_HISTORICAL_BARS",result["up"]["warnings"])
        self.assertFalse(result["up"]["sample_adequate_for_preliminary_review"])
    def test_measured_regime_exposure_with_trade_count_can_pass_screen(self):
        bars=[{"close":100} for _ in range(1100)]
        trades=[{"signal_index":i,"entry_index":i+1,"exit_index":i+2,"net_return":.001}
                for i in range(30,120,3)]
        result=regime_sample_review(bars,trades)
        self.assertEqual(result["sideways"]["trade_count"],30)
        self.assertEqual(result["sideways"]["regime_bars"],1080)
        self.assertTrue(result["sideways"]["sample_adequate_for_preliminary_review"])
        self.assertFalse(result["sideways"]["profitability_verified"])
    def test_short_regime_still_fails_bar_threshold_with_trade(self):
        bars=[{"close":100} for _ in range(50)]
        trades=[{"signal_index":25,"entry_index":26,"exit_index":27,"net_return":.01}]
        result=regime_sample_review(bars,trades,minimum_trades=1,minimum_bars=100)
        self.assertIn("INSUFFICIENT_HISTORICAL_BARS",result["sideways"]["warnings"])
if __name__=="__main__":unittest.main()
