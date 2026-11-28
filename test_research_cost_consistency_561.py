"""Cost sensitivity must reprice original OHLC, never double-charge slippage."""
import unittest
from badang_research_backtest_545 import evaluate_signal
from badang_research_cost_sensitivity_560 import cost_sensitivity

class CostRepricingConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100.0,"close":100.0} for _ in range(12)]
        self.bars[3]["open"]=105.0
        self.bars[6]["close"]=107.0
    def test_baseline_matches_original_backtest_exactly(self):
        for direction in ("long","short"):
            with self.subTest(direction=direction):
                trade=evaluate_signal(self.bars,2,direction,3,.0006,.0005)
                metrics=cost_sensitivity([trade])["scenarios"]["baseline"]["metrics"]
                self.assertAlmostEqual(metrics["compounded_net_return"],trade["net_return"])
    def test_zero_cost_matches_raw_price_return(self):
        trade=evaluate_signal(self.bars,2,"long",3,.0006,.0005)
        metrics=cost_sensitivity([trade],{"zero":(0,0)})["scenarios"]["zero"]["metrics"]
        self.assertAlmostEqual(metrics["compounded_net_return"],107/105-1)
    def test_higher_cost_never_improves_same_long_trade(self):
        trade=evaluate_signal(self.bars,2,"long",3)
        r=cost_sensitivity([trade])["scenarios"]
        self.assertGreater(r["baseline"]["metrics"]["compounded_net_return"],r["stress"]["metrics"]["compounded_net_return"])
if __name__=="__main__":unittest.main()
