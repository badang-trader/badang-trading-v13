"""Reject second-based, boolean, fractional and malformed exchange timestamps."""
import unittest
from badang_live_historical_research_551 import parse_exchange_timestamp,convert_closed_candles

class ExchangeTimestampTests(unittest.TestCase):
    def test_epoch_milliseconds_as_string_and_integer(self):
        self.assertEqual(parse_exchange_timestamp("1794000000000"),1794000000000)
        self.assertEqual(parse_exchange_timestamp(1794000000000),1794000000000)
    def test_epoch_seconds_rejected(self):
        for value in ("1794000000",1794000000):
            with self.subTest(value=value),self.assertRaises(ValueError):
                parse_exchange_timestamp(value)
    def test_boolean_float_and_scientific_notation_rejected(self):
        for value in (True,1794000000000.0,"1.794e12",None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                parse_exchange_timestamp(value)
    def test_negative_and_bad_digit_strings_rejected(self):
        for value in ("-1794000000000","179400000000a"," 1794000000000"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                parse_exchange_timestamp(value)
    def test_conversion_rejects_bad_timestamp_before_research(self):
        row=["1794000000","100","102","99","101","12"]
        with self.assertRaises(ValueError):
            convert_closed_candles({"candles":[row,row]})
if __name__=="__main__":unittest.main()
