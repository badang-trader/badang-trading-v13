"""Offline bounded Bitget research history safety tests; no network."""
import unittest
from badang_research_history_582 import research_history

STEP = 900000
NOW = 2000000 * STEP + 1234

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
                    if i != 1999950]
        r = research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "insufficient_history")
        self.assertEqual(r["stop_reason"], "historical_gap")
        self.assertEqual(r["confirmed_bars"], 49)

    def test_page_boundary_gap_rejects_1000_bar_sample(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)
                    if i != 1999600]
        r = research_history("BTCUSDT", "15m", target_bars=1000,
                             max_pages=6, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "insufficient_history")
        self.assertEqual(r["stop_reason"], "historical_gap")
        self.assertLess(r["confirmed_bars"], 1000)
        self.assertFalse(r["trading_ready"])

    def test_conflicting_overlap_fails_closed(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            rows = [candle(i) for i in range(end - 200, end)]
            if end < 2000001:
                rows.append(candle(1999801, 100.5))
            return rows
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)

    def test_1000_realistic_consecutive_bars_need_five_pages(self):
        requests = []
        def fetch(path, params):
            requests.append(params)
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)]
        r = research_history("BTCUSDT", "15m", target_bars=1000,
                             max_pages=6, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["confirmed_bars"], 1000)
        self.assertEqual(r["pages"], 5)
        self.assertEqual(len({x[0] for x in r["candles"]}), 1000)
        self.assertTrue(all(int(b[0]) - int(a[0]) == STEP
                            for a, b in zip(r["candles"], r["candles"][1:])))
        self.assertEqual(len(requests), 5)

    def test_rate_limit_propagates_without_unbounded_retry(self):
        calls = []
        def limited(path, params):
            calls.append(params)
            raise ValueError("Bitget 요청 제한(HTTP 429): 재시도 3회 실패")
        with self.assertRaisesRegex(ValueError, "429"):
            research_history("BTCUSDT", "15m", target_bars=1000,
                             max_pages=6, now_ms=NOW, fetch=limited)
        self.assertEqual(len(calls), 1)

    def test_unconfirmed_latest_candle_is_not_counted(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)]
        r = research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["confirmed_bars"], 205)
        self.assertLessEqual(int(r["candles"][-1][0]) + STEP, NOW)
        self.assertTrue(r["fresh"])

    def test_in_progress_candle_is_excluded_without_aborting_page(self):
        def fetch(path, params):
            end = int(params["endTime"]) // STEP
            return [candle(i) for i in range(end - 200, end)]
        r = research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["confirmed_bars"], 205)
        self.assertNotIn(str(2000000 * STEP),
                         [row[0] for row in r["candles"]])

    def test_stale_contiguous_history_is_not_adequate(self):
        def fetch(path, params):
            end = min(int(params["endTime"]) // STEP, 1999000)
            return [candle(i) for i in range(end - 200, end)]
        r = research_history("BTCUSDT", "15m", target_bars=205,
                             max_pages=2, now_ms=NOW, fetch=fetch)
        self.assertEqual(r["confirmed_bars"], 205)
        self.assertFalse(r["fresh"])
        self.assertEqual(r["status"], "insufficient_history")

    def test_malformed_ohlc_is_rejected_without_repair(self):
        def fetch(path, params):
            row = candle(1999999)
            row[2] = "98"  # high below open and close
            return [row]
        with self.assertRaisesRegex(ValueError, "Invalid Bitget historical candle"):
            research_history("BTCUSDT", "15m", target_bars=205,
                             now_ms=NOW, fetch=fetch)

    def test_rejects_invalid_and_future_candles(self):
        def future(path, params):
            return [candle(2000002)]
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
