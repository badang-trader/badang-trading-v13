"""Market regime exposure counts must be causal and cover only eligible bars."""
import unittest
from badang_research_regime_exposure_564 import regime_exposure

class RegimeExposureTests(unittest.TestCase):
    def test_constant_prices_are_sideways_after_warmup(self):
        bars=[{"close":100} for _ in range(40)]
        result=regime_exposure(bars)
        self.assertEqual(result["regime_bars"],{"up":0,"down":0,"sideways":20})
        self.assertEqual(result["unclassified_warmup_bars"],20)
    def test_short_history_has_no_classified_bars(self):
        result=regime_exposure([{"close":100} for _ in range(5)])
        self.assertEqual(result["classified_bars"],0)
        self.assertEqual(result["unclassified_warmup_bars"],5)
    def test_strong_trend_classifies_up_and_down(self):
        up=regime_exposure([{"close":100+i*2} for i in range(45)])
        down=regime_exposure([{"close":200-i*2} for i in range(45)])
        self.assertGreater(up["regime_bars"]["up"],0)
        self.assertGreater(down["regime_bars"]["down"],0)
    def test_future_candles_cannot_relabel_past_exposure(self):
        bars=[{"close":100+i} for i in range(40)]
        a=regime_exposure(bars)
        b=regime_exposure(bars+[{"close":1}])
        self.assertEqual(sum(a["regime_bars"].values()),sum(b["regime_bars"].values())-1)
        self.assertEqual(a["regime_bars"]["up"],b["regime_bars"]["up"])
        self.assertEqual(a["classified_bars"]+1,b["classified_bars"])
    def test_invalid_lookback_rejected(self):
        with self.assertRaises(ValueError):
            regime_exposure([{"close":100} for _ in range(30)],lookback=True)
if __name__=="__main__":unittest.main()
