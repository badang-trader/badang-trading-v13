"""Regression tests for the read-only live snapshot Bitget adapter."""
import unittest
from unittest.mock import patch
import requests
import badang_live_428 as live


class Live428SafetyTests(unittest.TestCase):
    def test_future_candle_is_rejected(self):
        row = [1_800_000_060_000, "100", "102", "99", "101", "5"]
        with self.assertRaisesRegex(ValueError, "Future"):
            live.normalize_candle(row, "1H", 1_800_000_000_000)

    def test_current_forming_candle_is_provisional(self):
        row = [1_800_000_000_000, "100", "102", "99", "101", "5"]
        candle = live.normalize_candle(row, "1H", 1_800_000_060_000)
        self.assertTrue(candle["forming"])

    def test_retry_adapter_only_retries_get(self):
        adapter = live.SESSION.get_adapter("https://api.bitget.com")
        retry = adapter.max_retries
        self.assertIn(429, retry.status_forcelist)
        self.assertIn("GET", retry.allowed_methods)
        self.assertNotIn("POST", retry.allowed_methods)

    def test_snapshot_rejects_conflicting_duplicate_timestamps(self):
        ticker = [{"lastPr": "100", "bidPr": "99", "askPr": "101"}]
        candles = [
            [1_800_000_000_000, "100", "102", "99", "101", "5"],
            [1_800_000_000_000, "100", "104", "98", "103", "6"],
        ]
        def fake_get(path, params):
            if path.endswith("/ticker"):
                return ticker
            if path.endswith("/candles"):
                return candles
            return []
        with patch.object(live.time, "time", return_value=1_800_000_060), patch.object(live, "get", side_effect=fake_get):
            result = live.snapshot("BTCUSDT", frames=("1H",))
        self.assertNotIn("1H", result["candles"])
        self.assertIn("Duplicate candle timestamp", result["errors"]["1H"])

    def test_snapshot_rejects_future_candle_without_fabricating_confirmation(self):
        ticker = [{"lastPr": "100", "bidPr": "99", "askPr": "101"}]
        future = [[1_800_000_060_000, "100", "102", "99", "101", "5"]]
        def fake_get(path, params):
            if path.endswith("/ticker"):
                return ticker
            if path.endswith("/candles"):
                return future
            return []
        with patch.object(live.time, "time", return_value=1_800_000_000), patch.object(live, "get", side_effect=fake_get):
            result = live.snapshot("BTCUSDT", frames=("1H",))
        self.assertNotIn("1H", result["candles"])
        self.assertIn("Future", result["errors"]["1H"])


if __name__ == "__main__":
    unittest.main()
