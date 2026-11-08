"""Future-dated exchange candles must fail closed."""
import unittest
from unittest.mock import patch
from bitget_market_data import fastest_candles

class FutureCandleSafetyTests(unittest.TestCase):
    def test_future_timestamp_rejected(self):
        step=900000
        now=1760000000000
        current=(now//step)*step
        candles=[[str(current-i*step),"100","101","99","100","10"] for i in range(220)]
        candles.append([str(current+step),"100","101","99","100","10"])
        with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",return_value=candles):
            with self.assertRaisesRegex(ValueError,"미래 시각"):
                fastest_candles("BTCUSDT","15m")

    def test_off_grid_candle_timestamp_rejected(self):
        step=900000
        now=1760000000000
        current=(now//step)*step
        candles=[[str(current-i*step),"100","101","99","100","10"] for i in range(220)]
        candles[30][0]=str(int(candles[30][0])+60000)
        with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",return_value=candles):
            with self.assertRaisesRegex(ValueError,"시각 정렬 오류"):
                fastest_candles("BTCUSDT","15m")

    def test_malformed_candle_structure_rejected(self):
        step=900000
        now=1760000000000
        current=(now//step)*step
        candles=[[str(current-i*step),"100","101","99","100","10"] for i in range(220)]
        candles[40]=[str(current-40*step),"100"]
        with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",return_value=candles):
            with self.assertRaisesRegex(ValueError,"잘못된 캔들 구조"):
                fastest_candles("BTCUSDT","15m")

    def test_invalid_ohlcv_does_not_get_silently_dropped(self):
        step=900000
        now=1760000000000
        current=(now//step)*step
        for column,value in [(2,"98"),(4,"nan"),(5,"-1")]:
            with self.subTest(column=column,value=value):
                candles=[[str(current-i*step),"100","101","99","100","10"] for i in range(220)]
                candles[40][column]=value
                with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",return_value=candles):
                    expected="Conflicting|잘못된 OHLCV" if value=="nan" else "잘못된 OHLCV"
                    with self.assertRaisesRegex(ValueError,expected):
                        fastest_candles("BTCUSDT","15m")

if __name__=="__main__":unittest.main()
