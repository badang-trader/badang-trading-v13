"""Safety and arithmetic regression tests for approximate volume profile."""
import unittest
from badang_volume_profile_542 import (approximate_volume_profile,
                                       support_volume_confluence,
                                       multi_timeframe_confluence)


def rows(n=120):
    result = []
    for i in range(n):
        p = 100 + i * 0.02 - (3 if i % 15 == 7 else 0)
        result.append({"open": p, "high": p + 1, "low": p - 1,
                       "close": p, "volume": 100})
    return result


class VolumeProfileTests(unittest.TestCase):
    def test_conserves_volume_approximately(self):
        data = rows()
        p = approximate_volume_profile(data)
        self.assertEqual(p["status"], "ok")
        self.assertAlmostEqual(sum(v["estimated_volume"] for v in p["levels"]),
                               sum(v["volume"] for v in data), delta=0.1)

    def test_no_future_candles_needed(self):
        p = approximate_volume_profile(rows())
        self.assertEqual(p["bars_used"], 120)
        self.assertFalse(p["trading_ready"])

    def test_rejects_invalid_data(self):
        data = rows()
        data[50]["volume"] = -1
        self.assertEqual(approximate_volume_profile(data)["status"], "invalid_data")

    def test_rejects_unconfirmed(self):
        p = support_volume_confluence(rows(), "BTC", "15m", confirmed=False)
        self.assertEqual(p["status"], "unconfirmed")
        self.assertEqual(p["zones"], [])

    def test_enriched_zones_do_not_execute(self):
        p = support_volume_confluence(rows(), "ETH", "1h")
        self.assertEqual(p["status"], "ok")
        self.assertFalse(p["trading_ready"])
        self.assertTrue(all("relative_volume_at_zone" in z for z in p["zones"]))

    def test_swing_timeframes(self):
        result = multi_timeframe_confluence({}, "BTC", "swing")
        self.assertEqual(set(result), {"1h", "4h", "1d"})

    def test_invalid_timeframe(self):
        with self.assertRaises(ValueError):
            support_volume_confluence(rows(), "BTC", "1d", "scalp")


if __name__ == "__main__":
    unittest.main()
