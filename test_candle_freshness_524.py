"""Read-only stale-market-data regression; no network or order execution."""
import unittest
from unittest.mock import patch
import bitget_market_data as market

STEP=900000
NOW=1800000000000

def page(latest):
    return [[str(latest-i*STEP),"100","102","99","101","10"] for i in range(230)]

class FreshnessTests(unittest.TestCase):
    def test_rejects_stale_history_even_with_205_bars(self):
        last=NOW-5*STEP
        with patch.object(market.time,"time",return_value=NOW/1000),patch.object(market,"_get",return_value=page(last)):
            with self.assertRaisesRegex(ValueError,"최근 확정봉 지연"):
                market.fastest_candles("BTCUSDT","15m")
    def test_accepts_recent_history(self):
        last=NOW-STEP
        with patch.object(market.time,"time",return_value=NOW/1000),patch.object(market,"_get",return_value=page(last)):
            result=market.fastest_candles("BTCUSDT","15m")
        self.assertGreaterEqual(len(result["candles"])-1,205)
        self.assertEqual(result["exchange"],"bitget")

if __name__=="__main__":
    unittest.main()
