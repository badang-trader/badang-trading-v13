"""Research clock is obtained from exchange, never derived from candle timestamps."""
import unittest
from unittest.mock import patch
from badang_exchange_clock_514 import bitget_server_clock_ms
from badang_research_ui import app

class ExchangeClockTests(unittest.TestCase):
    def test_valid_server_time(self):
        self.assertEqual(bitget_server_clock_ms(lambda path,params:{"serverTime":"1794888000000"}),1794888000000)
    def test_invalid_clocks_rejected(self):
        for value in (None,True,-1,"oops",1234,"1794888000000.2"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                bitget_server_clock_ms(lambda path,params:{"serverTime":value})
    def test_exchange_clock_unavailable_fails_closed(self):
        with patch("badang_research_ui.bitget_server_clock_ms",side_effect=ValueError("missing_exchange_clock")),patch("badang_research_ui.research_history") as history:
            response=app.test_client().get("/api/research-514?symbol=BTC&frame=1h")
        self.assertEqual(response.status_code,422)
        self.assertEqual(response.get_json()["status"],"data_error")
        history.assert_not_called()
    def test_history_uses_exchange_clock_not_last_candle(self):
        with patch("badang_research_ui.bitget_server_clock_ms",return_value=1794888000000),patch("badang_research_ui.research_history",return_value={"status":"insufficient_history","confirmed_bars":0}) as history:
            response=app.test_client().get("/api/research-514?symbol=BTC&frame=1h")
        self.assertEqual(response.status_code,200)
        self.assertEqual(history.call_args.kwargs["now_ms"],1794888000000)
if __name__=="__main__":
    unittest.main()
