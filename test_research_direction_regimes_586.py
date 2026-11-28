"""Regime labels must use signal-time history, never future candles."""
import unittest
from badang_research_direction_regimes_586 import direction_by_regime

def candles():
    return [{"close": 100.0} for _ in range(60)]

def trade(direction="short"):
    return {"signal_index": 30, "entry_index": 31, "exit_index": 34,
            "direction": direction, "net_return": -0.01}

class RegimeDirectionTests(unittest.TestCase):
    def test_signal_time_downtrend_short(self):
        rows = candles()
        rows[10]["close"] = 100
        rows[30]["close"] = 90
        result = direction_by_regime(rows, [trade()])
        self.assertEqual(result["groups"]["down"]["short"]["completed_trades"], 1)
        self.assertEqual(result["groups"]["up"]["short"]["completed_trades"], 0)

    def test_future_candles_cannot_change_signal_regime(self):
        rows = candles()
        rows[10]["close"] = 100
        rows[30]["close"] = 90
        before = direction_by_regime(rows, [trade()])
        for i in range(31, 60):
            rows[i]["close"] = 100000
        after = direction_by_regime(rows, [trade()])
        self.assertEqual(before, after)

    def test_uptrend_long_and_empty_short(self):
        rows = candles()
        rows[10]["close"] = 100
        rows[30]["close"] = 105
        result = direction_by_regime(rows, [trade("long")])
        self.assertEqual(result["groups"]["up"]["long"]["completed_trades"], 1)
        self.assertIsNone(result["groups"]["up"]["short"]["metrics"])

    def test_invalid_direction_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            direction_by_regime(candles(), [trade("wait")])

if __name__ == "__main__":
    unittest.main()
