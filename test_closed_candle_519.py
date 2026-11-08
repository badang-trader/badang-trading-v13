"""Regression: legacy scan must not analyze unfinished or placeholder candles."""
import unittest
from unittest.mock import patch
import app

class ClosedCandleTests(unittest.TestCase):
    def test_excludes_last_row_even_if_it_looks_real(self):
        data=[["1000","1","2","1","1.5","10"] for _ in range(206)]
        data[-1]=["2000","1","999","1","999","1000000"]
        with patch("bitget_market_data.fastest_candles",return_value={"candles":data,"exchange":"bitget"}):
            rows=app.candles("BTCUSDT","15m")
        self.assertEqual(len(rows),205)
        self.assertEqual(rows[-1][4],"1.5")
        self.assertNotIn("999",[r[4] for r in rows])

    def test_fails_closed_if_confirmed_history_insufficient(self):
        data=[["1000","1","2","1","1.5","10"] for _ in range(205)]
        with patch("bitget_market_data.fastest_candles",return_value={"candles":data,"exchange":"bitget"}):
            with self.assertRaisesRegex(ValueError,"확정봉 부족"):
                app.candles("ETHUSDT","1D")

if __name__=="__main__": unittest.main()
