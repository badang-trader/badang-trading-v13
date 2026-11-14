"""Ensure legacy candle selection never falls back to other exchanges."""
import unittest
from unittest.mock import patch
from exchange_data import fastest_candles


class BitgetOnlyExchangeTests(unittest.TestCase):
    def test_other_exchanges_rejected_without_network(self):
        for exchanges in (["okx"], ["binance"], ["bitget", "okx"],
                          [], "bitget", ["BITGET"]):
            with self.subTest(exchanges=exchanges):
                with patch("exchange_data.bitget_candles") as bitget, \
                     patch("exchange_data.okx_candles") as okx, \
                     patch("exchange_data.binance_candles") as binance:
                    with self.assertRaises(ValueError):
                        fastest_candles("BTCUSDT", "1h", exchanges=exchanges)
                    bitget.assert_not_called()
                    okx.assert_not_called()
                    binance.assert_not_called()

    def test_bitget_failure_never_falls_back_to_other_exchange(self):
        with patch("exchange_data.bitget_candles",
                   side_effect=RuntimeError("Bitget temporarily unavailable")) as bitget, \
             patch("exchange_data.okx_candles") as okx, \
             patch("exchange_data.binance_candles") as binance:
            with self.assertRaisesRegex(ValueError, "All exchanges failed"):
                fastest_candles("BTCUSDT", "1h")
            bitget.assert_called_once()
            okx.assert_not_called()
            binance.assert_not_called()

    def test_default_only_calls_bitget(self):
        rows = [{"timestamp": i * 3600000, "open": 100, "high": 101,
                 "low": 99, "close": 100, "volume": 10} for i in range(230)]
        with patch("exchange_data.bitget_candles", return_value=rows) as bitget, \
             patch("exchange_data.validate_candles", return_value=rows), \
             patch("exchange_data.okx_candles") as okx, \
             patch("exchange_data.binance_candles") as binance:
            result = fastest_candles("BTCUSDT", "1h")
        self.assertEqual(result["exchange"], "bitget")
        bitget.assert_called_once()
        okx.assert_not_called()
        binance.assert_not_called()


if __name__ == "__main__":
    unittest.main()
