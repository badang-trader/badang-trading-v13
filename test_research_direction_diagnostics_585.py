"""Regression checks for long/short attribution without trade filtering."""
import unittest
from badang_research_direction_diagnostics_585 import direction_diagnostics

class DirectionDiagnosticsTests(unittest.TestCase):
    def test_counts_and_losses_remain_separate(self):
        trades = [
            {"entry_index": 1, "exit_index": 3, "direction": "long", "net_return": -0.02},
            {"entry_index": 5, "exit_index": 7, "direction": "short", "net_return": 0.01},
            {"entry_index": 9, "exit_index": 11, "direction": "long", "net_return": -0.01},
        ]
        report = direction_diagnostics(trades)
        self.assertEqual(report["long"]["completed_trades"], 2)
        self.assertEqual(report["short"]["completed_trades"], 1)
        self.assertAlmostEqual(report["long"]["mean_net_return_per_trade"], -0.015)
        self.assertAlmostEqual(report["short"]["mean_net_return_per_trade"], 0.01)

    def test_empty_side_has_no_fabricated_performance(self):
        trades = [{"entry_index": 1, "exit_index": 3,
                   "direction": "long", "net_return": -0.02}]
        report = direction_diagnostics(trades)
        self.assertIsNone(report["short"]["metrics"])
        self.assertIsNone(report["short"]["mean_net_return_per_trade"])

    def test_unknown_direction_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected trade direction"):
            direction_diagnostics([{"direction": "wait", "net_return": 0.0}])

if __name__ == "__main__":
    unittest.main()
