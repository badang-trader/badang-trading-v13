"""Offline bounded Bitget research history safety tests; no network."""
import unittest
from badang_research_history_582 import research_history

STEP = 900000
NOW = 100000 * STEP + 1234

def candle(i, close=100):
    return [str(i * STEP), "100", "101", "99", str(close), "100"]

class ResearchHistoryTests(unittest.TestCase):
    def test_pagination_recovers_205_confirmed_bars(self):
        calls = []
        def fetch(path, params):
            calls.append((path, params))
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)]
        r = research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=3, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["confirmed_bars"], 205)
        self.assertEqual(r["pages"], 2)
        self.assertTrue(all(x[1]["productType"] == "USDT-FUTURES" for x in calls))
        self.assertFalse(r["trading_ready"])

    def test_page_budget_cannot_claim_adequacy(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)]
        r = research_history("ETHUSDT", "15m", target_bars=1000,
                             max_pages=2, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "insufficient_history")
        self.assertEqual(r["pages"], 2)

    def test_missing_bar_is_not_interpolated(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)
                    if i != 99950]
        r = research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "insufficient_history")
        self.assertEqual(r["stop_reason"], "historical_gap")
        self.assertEqual(r["confirmed_bars"], 49)

    def test_conflicting_overlap_fails_closed(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            rows = [candle(i) for i in range(end - 200, end)]
            if end < 100001:
                rows.append(candle(99801, 100.5))
            return rows
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)

    def test_rejects_invalid_and_future_candles(self):
        def future(path, params):
            return [candle(100002)]
        with self.assertRaisesRegex(ValueError, "Invalid"):
            research_history("BTCUSDT", "15m", target_bars=205,
                             now_ms=NOW, fetch=future)
        with self.assertRaises(ValueError):
            research_history("BTCUSDT", "15m", target_bars=1500,
                             now_ms=NOW, fetch=future)
        with self.assertRaises(ValueError):
            research_history("BTCUSDT", "15m", max_pages=7,
                             now_ms=NOW, fetch=future)

if __name__ == "__main__":
    unittest.main()
