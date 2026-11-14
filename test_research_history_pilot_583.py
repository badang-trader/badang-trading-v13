"""Offline pilot orchestration tests; no Bitget network calls."""
import unittest
from unittest.mock import patch
from badang_research_history_pilot_583 import pilot

class ResearchPilotTests(unittest.TestCase):
    def test_four_targets_are_read_only_and_report_coverage(self):
        calls = []
        def fake(symbol, frame, **kw):
            calls.append((symbol, frame, kw["target_bars"], kw["max_pages"]))
            return {"status": "ok", "confirmed_bars": 1000,
                    "pages": 6, "fresh": True, "stop_reason": "target_reached",
                    "target_bars": 1000}
        with patch("badang_research_history_pilot_583.research_history",
                   side_effect=fake):
            report = pilot()
        self.assertEqual(report["target_count"], 4)
        self.assertEqual(report["adequate_targets"], 4)
        self.assertFalse(report["trading_ready"])
        self.assertEqual(len(set(calls)), 4)
        self.assertTrue(all(t == 1000 and p == 6 for _, _, t, p in calls))

    def test_partial_failure_is_not_marked_adequate(self):
        def fake(symbol, frame, **kw):
            if symbol == "ETHUSDT":
                raise ValueError("rate limited")
            return {"status": "insufficient_history", "confirmed_bars": 400,
                    "pages": 6, "fresh": True}
        with patch("badang_research_history_pilot_583.research_history",
                   side_effect=fake):
            report = pilot()
        self.assertEqual(report["adequate_targets"], 0)
        self.assertEqual(sum(r["status"] == "error" for r in report["results"]), 2)
        self.assertTrue(report["read_only"])

if __name__ == "__main__":
    unittest.main()
