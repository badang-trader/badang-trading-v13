"""Regression checks for causal support-touch research."""
import unittest
from unittest.mock import patch
from badang_research_regimes_555 import regime_at
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
        result = support_touch_backtest(bars(), "BTC", "15m", exchange_now_ms=130*STEP)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["trading_ready"])
        self.assertEqual(sum(result["counts"].values()), len(result["events"]))

    def test_small_samples_suppress_fraction(self):
        result = support_touch_backtest(bars(), "ETH", "15m", exchange_now_ms=130*STEP)
        self.assertFalse(result["sample_adequate"])
        self.assertIsNone(result["observed_rebound_fraction"])

    def test_future_candle_change_does_not_change_earlier_zone(self):
        data = bars()
        before = support_touch_backtest(data, "BTC", "15m", exchange_now_ms=130*STEP)
        changed = bars()
        changed[-1]["high"] += 30
        after = support_touch_backtest(changed, "BTC", "15m", exchange_now_ms=130*STEP)
        self.assertEqual(before["events"], after["events"])

    def test_regime_at_touch_uses_only_pre_touch_closes(self):
        data = bars()
        zone = {"status":"historical_support","lower":98.0,"upper":105.0,
                "center":101.5,"evidence_score":2,"evidence_grade":"limited_evidence"}
        with patch("badang_support_backtest_545.validated_support_reliability",
                   return_value={"status":"ok","zones":[zone]}):
            original = support_touch_backtest(data,"BTC","15m",
                                               exchange_now_ms=130*STEP)
            changed = bars()
            changed[90]["close"] = changed[90]["open"] + 0.5
            altered = support_touch_backtest(changed,"BTC","15m",
                                              exchange_now_ms=130*STEP)
        self.assertTrue(original["events"])
        self.assertEqual(original["events"][0]["touch_bar_index"],90)
        self.assertEqual(original["events"][0]["regime_before_touch"],
                         altered["events"][0]["regime_before_touch"])
        self.assertEqual(original["events"][0]["regime_before_touch"],
                         regime_at(data,89))

    def test_gap_rejected(self):
        data = bars()
        data[70]["timestamp"] += 1
        self.assertEqual(support_touch_backtest(data, "BTC", "15m", exchange_now_ms=130*STEP)["status"],
                         "misaligned_timestamp")

    def test_missing_trusted_clock(self):
        self.assertEqual(support_touch_backtest(bars(), "BTC", "15m")["status"],
                         "missing_exchange_clock")

    def test_unclosed_last_candle(self):
        self.assertEqual(support_touch_backtest(
            bars(), "BTC", "15m", exchange_now_ms=130*STEP-1)["status"],
            "open_or_future_candle")

    def test_invalid_horizon(self):
        with self.assertRaises(ValueError):
            support_touch_backtest(bars(), "BTC", "15m", horizon=0, exchange_now_ms=130*STEP)

if __name__ == "__main__":
    unittest.main()
