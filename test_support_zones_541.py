"""Regression tests for informational BTC/ETH support zones."""
import unittest
from badang_support_zones_541 import support_zones, multi_timeframe_support


def candles(n=120):
    rows = []
    for i in range(n):
        # Repeated local swing lows below a gently rising reference close.
        base = 100 + i * 0.02
        dip = 3 if i % 15 == 7 else 0
        close = base - dip
        rows.append({"open": close, "high": close + 1,
                     "low": close - 1, "close": close, "volume": 100})
    return rows


class SupportZonesTests(unittest.TestCase):
    def test_multiple_levels_are_below_price_and_ordered(self):
        result = support_zones(candles(), "BTC-USDT", "15m")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["trading_ready"])
        self.assertTrue(result["zones"])
        self.assertLessEqual(len(result["zones"]), 5)
        centers = [z["center"] for z in result["zones"]]
        self.assertEqual(centers, sorted(centers, reverse=True))
        self.assertTrue(all(z["upper"] < result["reference_close"] for z in result["zones"]))

    def test_broken_historical_support_is_not_reintroduced(self):
        data = [{"open": 100, "high": 101, "low": 99,
                 "close": 100, "volume": 100} for _ in range(120)]
        for i in (20, 40):
            data[i]["low"] = 90
        # A later confirmed close below the old 90 support invalidates it.
        data[60].update({"open": 100, "high": 101, "low": 84,
                         "close": 85})
        data[-1].update({"open": 100, "high": 111, "low": 99,
                         "close": 110})
        result = support_zones(data, "BTC", "15m")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(any(89 <= z["center"] <= 91
                             for z in result["zones"]))

    def test_identical_timeframe_zones_report_confluence(self):
        same = candles()
        result = multi_timeframe_support(
            {"1h": same, "4h": same, "1d": same}, "BTC", "swing")
        for tf, item in result.items():
            self.assertEqual(item["status"], "ok")
            self.assertTrue(item["zones"])
            for zone in item["zones"]:
                self.assertEqual(zone["timeframe_confluence_count"], 3)
                self.assertEqual(set(zone["overlapping_timeframes"]),
                                 {"1h", "4h", "1d"} - {tf})

    def test_missing_timeframe_does_not_inflate_confluence(self):
        result = multi_timeframe_support(
            {"1h": candles()}, "BTC", "swing")
        self.assertEqual(result["4h"]["status"], "insufficient_history")
        self.assertEqual(result["1d"]["status"], "insufficient_history")
        self.assertTrue(result["1h"]["zones"])
        self.assertTrue(all(z["timeframe_confluence_count"] == 1
                            and z["overlapping_timeframes"] == []
                            for z in result["1h"]["zones"]))

    def test_boolean_pivot_settings_rejected(self):
        for kwargs in ({"radius": True}, {"radius": False},
                       {"max_zones": True}, {"max_zones": False}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    support_zones(candles(), "BTC", "15m", **kwargs)

    def test_invalid_middle_bar_fails_closed(self):
        data = candles()
        data[44]["high"] = 0
        self.assertEqual(support_zones(data, "ETH", "1h")["status"], "invalid_data")

    def test_unconfirmed_candles_not_analyzed(self):
        self.assertEqual(support_zones(candles(), "BTC", "1h", confirmed=False)["zones"], [])

    def test_mode_timeframes(self):
        self.assertEqual(set(multi_timeframe_support({}, "ETH", "swing")),
                         {"1h", "4h", "1d"})
        with self.assertRaises(ValueError):
            support_zones(candles(), "BTC", "1d", "scalp")

    def test_malformed_timeframe_and_mode_raise_value_error(self):
        for timeframe, mode in ((None, "scalp"), ([], "scalp"),
                                ("15m", None), ("15m", []),
                                ("15m", 123)):
            with self.subTest(timeframe=timeframe, mode=mode):
                with self.assertRaises(ValueError):
                    support_zones(candles(), "BTC", timeframe, mode)
        for mode in (None, [], 123):
            with self.subTest(multi_mode=mode):
                with self.assertRaises(ValueError):
                    multi_timeframe_support({}, "BTC", mode)

    def test_malformed_candle_collection_fails_closed(self):
        for data in (None, 123, True, "not candles", {"bars": candles()}):
            with self.subTest(data_type=type(data).__name__):
                result = support_zones(data, "BTC", "15m")
                self.assertEqual(result["status"], "invalid_data")
                self.assertEqual(result["zones"], [])
                self.assertFalse(result["trading_ready"])

    def test_malformed_symbol_is_rejected_cleanly(self):
        for symbol in (None, 123, True, "", "   ", []):
            with self.subTest(symbol=symbol):
                with self.assertRaises(ValueError):
                    support_zones(candles(), symbol, "15m")

    def test_rejects_unsupported_symbol(self):
        with self.assertRaises(ValueError):
            support_zones(candles(), "SOL", "15m")

    def test_short_history_returns_no_levels(self):
        self.assertEqual(support_zones(candles(20), "ETH", "4h", "swing")["zones"], [])


if __name__ == "__main__":
    unittest.main()
