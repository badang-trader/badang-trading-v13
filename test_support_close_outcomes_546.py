"""Regression for close-based outcomes: a wick is not a confirmed rebound."""
import unittest
from unittest.mock import patch
from badang_support_backtest_545 import support_touch_backtest

STEP = 900000


def bars():
    data = []
    for i in range(105):
        data.append({"timestamp": i*STEP, "open": 100, "high": 101,
                     "low": 99, "close": 100, "volume": 100})
    return data


def fake_support(candles, symbol, timeframe, mode, *, exchange_now_ms):
    return {"status": "ok", "zones": [{
        "status": "historical_support", "lower": 99.0,
        "upper": 100.5, "center": 100, "evidence_score": 75
    }]}


class CloseOutcomeTests(unittest.TestCase):
    def test_wick_only_rebound_does_not_count(self):
        data = bars()
        data[90]["low"] = 99
        for i in range(91, 99):
            data[i]["high"] = 105
            data[i]["close"] = 100
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=fake_support):
            result = support_touch_backtest(
                data, "BTC", "15m", exchange_now_ms=len(data)*STEP)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["events"][0]["outcome"], "unresolved")

    def test_confirmed_close_counts(self):
        data = bars()
        data[91]["open"] = 100
        data[91]["high"] = 103
        data[91]["close"] = 102
        with patch("badang_support_backtest_545.validated_support_reliability",
                   side_effect=fake_support):
            result = support_touch_backtest(
                data, "ETH", "15m", exchange_now_ms=len(data)*STEP)
        self.assertEqual(result["events"][0]["outcome"], "rebound")


if __name__ == "__main__":
    unittest.main()
