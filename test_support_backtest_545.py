"""Regression checks for causal support-touch research."""
import unittest
from badang_support_backtest_545 import support_touch_backtest

STEP = 900000

def bars(n=130):
    out = []
    for i in range(n):
        p = 100 + i * .02 - (3 if i % 15 == 7 else 0)
        out.append({"timestamp": i * STEP, "open": p, "high": p + 1,
                    "low": p - 1, "close": p, "volume": 100})
    return out

class BacktestTests(unittest.TestCase):
    def test_results_never_claim_trading_ready(self):
        result = support_touch_backtest(bars(), "BTC", "15m")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["trading_ready"])
        self.assertEqual(sum(result["counts"].values()), len(result["events"]))

    def test_small_samples_suppress_fraction(self):
        result = support_touch_backtest(bars(), "ETH", "15m")
        self.assertFalse(result["sample_adequate"])
        self.assertIsNone(result["observed_rebound_fraction"])

    def test_future_candle_change_does_not_change_earlier_zone(self):
        data = bars()
        before = support_touch_backtest(data, "BTC", "15m")
        changed = bars()
        changed[-1]["high"] += 30
        after = support_touch_backtest(changed, "BTC", "15m")
        self.assertEqual(before["events"], after["events"])

    def test_gap_rejected(self):
        data = bars()
        data[70]["timestamp"] += 1
        self.assertEqual(support_touch_backtest(data, "BTC", "15m")["status"],
                         "misaligned_timestamp")

    def test_invalid_horizon(self):
        with self.assertRaises(ValueError):
            support_touch_backtest(bars(), "BTC", "15m", horizon=0)

if __name__ == "__main__":
    unittest.main()
