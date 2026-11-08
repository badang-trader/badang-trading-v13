"""Historical net-return sensitivity to assumed execution costs."""
import unittest
from badang_research_cost_sensitivity_560 import cost_sensitivity

class CostSensitivityTests(unittest.TestCase):
    def test_higher_costs_reduce_net_performance(self):
        trades=[{"actual_entry":100,"actual_exit":101,"direction":"long"}]
        result=cost_sensitivity(trades)
        scenarios=result["scenarios"]
        returns=[scenarios[k]["metrics"]["compounded_net_return"] for k in ("baseline","elevated","stress")]
        self.assertGreater(returns[0],returns[1])
        self.assertGreater(returns[1],returns[2])
    def test_small_gross_gain_can_turn_negative(self):
        trades=[{"actual_entry":100,"actual_exit":100.5,"direction":"long"}]
        result=cost_sensitivity(trades)["scenarios"]
        self.assertGreater(result["baseline"]["metrics"]["compounded_net_return"],0)
        self.assertLess(result["stress"]["metrics"]["compounded_net_return"],0)
    def test_empty_trades_never_claim_profit(self):
        result=cost_sensitivity([])["scenarios"]
        self.assertTrue(all(v["metrics"] is None for v in result.values()))
    def test_invalid_costs_rejected(self):
        trade=[{"actual_entry":100,"actual_exit":101,"direction":"long"}]
        for costs in ((-0.1,0),(0,float("nan"))):
            with self.subTest(costs=costs),self.assertRaises(ValueError):
                cost_sensitivity(trade,{"bad":costs})
if __name__=="__main__":unittest.main()
