"""Offline safety tests for research-only 1000-bar adapter."""
import unittest
from unittest.mock import patch
import badang_research_1000_backtest_584 as m

STEP = 900000
START = 1700000100000
START -= START % STEP

def bars(n=1000):
    return [[str(START + i * STEP), "100", "102", "99", "101", "10"]
            for i in range(n)]

class Research1000Tests(unittest.TestCase):
    def test_missing_history_does_not_invoke_backtest(self):
        with patch.object(m, "research_history", return_value={
                "status": "insufficient_history", "confirmed_bars": 400,
                "stop_reason": "historical_gap"}), patch.object(
                m, "research_engine_backtest") as engine:
            result = m.evaluate_target("BTCUSDT", "15m", "scalp")
        engine.assert_not_called()
        self.assertEqual(result["status"], "insufficient_history")
        self.assertFalse(result["trading_ready"])

    def test_exact_confirmed_1000_bars_reach_engine_and_costs(self):
        calls = []
        def engine(candles, **kw):
            calls.append((len(candles), kw))
            return {"trades": [], "summary": None}
        with patch.object(m, "research_history", return_value={
                "status": "ok", "candles": bars()}):
            result = m.evaluate_target("BTCUSDT", "15m", "scalp",
                                       engine=engine)
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["confirmed_bars"], 1000)
        self.assertEqual(result["completed_trades"], 0)
        self.assertFalse(result["trading_ready"])
        self.assertFalse(result["sample_assessment"][
            "sample_adequate_for_preliminary_review"])
        self.assertEqual(calls[0][0], 1000)
        self.assertEqual(calls[0][1]["fee_per_side"], 0.0006)
        self.assertEqual(calls[0][1]["slippage_per_side"], 0.0005)

    def test_malformed_history_fails_before_engine(self):
        corrupted = bars()
        corrupted[500][2] = "98"
        with patch.object(m, "research_history", return_value={
                "status": "ok", "candles": corrupted}), patch.object(
                m, "research_engine_backtest") as engine:
            with self.assertRaises(ValueError):
                m.evaluate_target("BTCUSDT", "15m", "scalp")
        engine.assert_not_called()

if __name__ == "__main__":
    unittest.main()
