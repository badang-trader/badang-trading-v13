"""Ensure live read-only research covers every requested Bitget timeframe."""
import unittest
from badang_live_historical_research_551 import TARGETS, FRAME_INTERVAL_MS


class LiveResearchTimeframeTests(unittest.TestCase):
    def test_btc_eth_scalp_and_swing_coverage(self):
        expected = {
            (symbol, frame, mode)
            for symbol in ("BTCUSDT", "ETHUSDT")
            for frame, mode in (
                ("15m", "scalp"), ("30m", "scalp"), ("1H", "scalp"),
                ("1H", "swing"), ("4H", "swing"), ("1D", "swing"))
        }
        self.assertEqual(set(TARGETS), expected)
        self.assertEqual(len(TARGETS), len(expected))
        self.assertTrue(all(frame in FRAME_INTERVAL_MS for _, frame, _ in TARGETS))


if __name__ == "__main__":
    unittest.main()
