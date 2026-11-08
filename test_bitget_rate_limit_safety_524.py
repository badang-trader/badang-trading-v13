"""Guard against amplifying Bitget 429 and network failures on candle fetch."""
import unittest
from unittest.mock import patch
import requests
import bitget_market_data as market

class CandleRetrySafetyTests(unittest.TestCase):
    def test_exhausted_429_is_not_retried_as_smaller_page(self):
        with patch.object(market, "_get", side_effect=ValueError("Bitget 요청 제한(HTTP 429): 재시도 3회 실패")) as get:
            with self.assertRaisesRegex(ValueError, "429"):
                market.fastest_candles("BTCUSDT", "1D")
            self.assertEqual(get.call_count, 1)
    def test_transport_error_is_not_retried_as_smaller_page(self):
        with patch.object(market, "_get", side_effect=requests.Timeout("timeout")) as get:
            with self.assertRaises(requests.Timeout):
                market.fastest_candles("BTCUSDT", "4H")
            self.assertEqual(get.call_count, 1)
    def test_invalid_page_size_falls_back_once(self):
        calls=[]
        def get(path,params):
            calls.append(params["limit"])
            if len(calls)==1:
                raise ValueError("Bitget API error: invalid limit range")
            return []
        with patch.object(market, "_get", side_effect=get):
            with self.assertRaisesRegex(ValueError, "확정봉 자료 없음"):
                market.fastest_candles("BTCUSDT", "1D")
        self.assertEqual(calls, ["350", "200"])

if __name__=="__main__":
    unittest.main()
