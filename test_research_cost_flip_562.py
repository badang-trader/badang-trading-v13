"""Execution-cost flip counts distinguish gross winners from net winners."""
import unittest
from badang_research_cost_sensitivity_560 import cost_sensitivity

class CostFlipTests(unittest.TestCase):
    def test_gross_winner_erased_only_by_stress(self):
        trades=[{"raw_entry":100,"raw_exit":100.5,"direction":"long"}]
        result=cost_sensitivity(trades)["scenarios"]
        self.assertEqual(result["baseline"]["gross_winners_turning_nonpositive"],0)
        self.assertEqual(result["stress"]["gross_winners_turning_nonpositive"],1)
        self.assertEqual(result["stress"]["net_winning_trades"],0)
    def test_gross_loser_not_miscounted_as_erased_winner(self):
        trades=[{"raw_entry":100,"raw_exit":90,"direction":"long"}]
        result=cost_sensitivity(trades)["scenarios"]
        self.assertTrue(all(v["gross_winners_turning_nonpositive"]==0 for v in result.values()))
    def test_short_direction_cost_flip(self):
        trades=[{"raw_entry":100,"raw_exit":99.5,"direction":"short"}]
        result=cost_sensitivity(trades)["scenarios"]
        self.assertEqual(result["stress"]["gross_winners_turning_nonpositive"],1)
    def test_empty_trades_zero_counts_and_no_metrics(self):
        result=cost_sensitivity([])["scenarios"]
        self.assertTrue(all(v["gross_winners_turning_nonpositive"]==0 and v["net_winning_trades"]==0 and v["metrics"] is None for v in result.values()))
if __name__=="__main__":unittest.main()
