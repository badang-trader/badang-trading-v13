"""Verify cost-aware research performance summaries."""
import unittest
from badang_research_metrics_546 import summarize_net_returns as summary

class ResearchMetricsTests(unittest.TestCase):
    def test_compounding_and_peak_drawdown(self):
        s=summary([0.10,-0.20,0.10])
        self.assertEqual(s["trades"],3)
        self.assertEqual(s["wins"],2)
        self.assertAlmostEqual(s["win_rate"],2/3)
        self.assertAlmostEqual(s["compounded_net_return"],1.1*0.8*1.1-1)
        self.assertAlmostEqual(s["max_drawdown"],0.2)
        self.assertAlmostEqual(s["profit_factor"],1)
    def test_all_wins_no_loss_denominator(self):
        s=summary([0.01,0.02])
        self.assertIsNone(s["profit_factor"])
        self.assertEqual(s["max_drawdown"],0)
    def test_losses_have_zero_win_rate(self):
        s=summary([-0.1,-0.2])
        self.assertEqual(s["win_rate"],0)
        self.assertAlmostEqual(s["max_drawdown"],0.28)
    def test_invalid_returns_rejected(self):
        for values in ([],[float("nan")],[float("inf")],[-1],[-1.2],[True]):
            with self.subTest(values=values),self.assertRaises(ValueError):
                summary(values)
    def test_overflow_rejected(self):
        with self.assertRaisesRegex(ValueError,"overflow"):
            summary([1e308,1e308])
if __name__=="__main__":unittest.main()
