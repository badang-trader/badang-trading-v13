"""Deterministic equity-curve checks for research-only unlevered returns."""
import unittest
from badang_research_metrics_546 import summarize_net_returns as summarize

class ResearchDrawdownTests(unittest.TestCase):
    def test_two_losses_compound_not_add(self):
        result=summarize([-0.1,-0.1])
        self.assertAlmostEqual(result["compounded_net_return"],-0.19)
        self.assertAlmostEqual(result["max_drawdown"],0.19)
        self.assertEqual(result["win_rate"],0)
    def test_recovery_does_not_erase_historical_drawdown(self):
        result=summarize([0.2,-0.25,1/3])
        self.assertAlmostEqual(result["compounded_net_return"],0.2)
        self.assertAlmostEqual(result["max_drawdown"],0.25)
    def test_new_high_resets_drawdown_peak(self):
        result=summarize([0.1,-0.05,0.2,-0.1])
        self.assertAlmostEqual(result["max_drawdown"],0.1)
    def test_all_wins_have_zero_drawdown(self):
        result=summarize([0.02,0.03,0.01])
        self.assertEqual(result["max_drawdown"],0)
        self.assertEqual(result["profit_factor"],None)
    def test_flat_trade_does_not_count_as_win(self):
        result=summarize([0.0,-0.1,0.0])
        self.assertEqual(result["wins"],0)
        self.assertAlmostEqual(result["profit_factor"],0)
    def test_loss_of_full_capital_rejected(self):
        for value in (-1,-1.01):
            with self.subTest(value=value),self.assertRaises(ValueError):
                summarize([value])
if __name__=="__main__":unittest.main()
