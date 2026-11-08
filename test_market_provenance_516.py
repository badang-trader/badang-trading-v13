"""Offline regression checks for single-venue candle provenance and stale-data handling."""
import unittest
from unittest.mock import patch
import app


class CoherentFrameTests(unittest.TestCase):
    def test_accepts_only_single_venue_and_fresh_frames(self):
        calls = []
        def fetch(symbol, timeframe, exchanges=None):
            calls.append((symbol, timeframe, exchanges))
            return {"exchange": "bitget", "candles": [timeframe]}
        with patch.object(app, "inspect_frame_410", side_effect=lambda data, tf: {"status": "OK", "last_closed_age_minutes": 1}):
            frames, audits, venue, attempts = app.coherent_frames_416("BTCUSDT", ["15m", "1H"], fetch)
        self.assertEqual(venue, "bitget")
        self.assertEqual(set(frames), {"15m", "1H"})
        self.assertEqual(calls, [("BTCUSDT", "15m", ["bitget"]), ("BTCUSDT", "1H", ["bitget"])])
        self.assertFalse(attempts)

    def test_rejects_other_venue_even_when_fetcher_returns_data(self):
        def fetch(symbol, timeframe, exchanges=None):
            return {"exchange": "okx", "candles": [timeframe]}
        with self.assertRaises(ValueError):
            app.coherent_frames_416("BTCUSDT", ["15m"], fetch)

    def test_stale_candles_are_not_certified_as_fresh(self):
        def fetch(symbol, timeframe, exchanges=None):
            return {"exchange": "bitget", "candles": [timeframe]}
        with patch.object(app, "inspect_frame_410", return_value={"status": "OK", "last_closed_age_minutes": 999}):
            frames, audits, venue, attempts = app.coherent_frames_416("BTCUSDT", ["15m"], fetch)
        self.assertEqual(venue, "bitget")
        self.assertFalse(app.frame_freshness_416(audits["15m"], "15m")[0])
        self.assertTrue(attempts)

    def test_unverified_audit_is_not_fresh(self):
        self.assertFalse(app.frame_freshness_416({"status": "CHECK", "last_closed_age_minutes": 0}, "15m")[0])


if __name__ == "__main__":
    unittest.main()
