"""Fail-closed historical exchange OHLCV conversion tests."""
import unittest
from badang_live_historical_research_551 import convert_closed_candles

class ExchangeOHLCVTests(unittest.TestCase):
    def setUp(self):
        self.row=["1794000000000","100","102","99","101","0"]
        self.last=["1794000900000","100","102","99","101","1"]
    def convert(self,row):
        return convert_closed_candles({"candles":[row,self.last]})
    def test_zero_volume_valid(self):
        self.assertEqual(self.convert(self.row)[0]["volume"],0)
    def test_negative_volume_rejected(self):
        row=list(self.row);row[5]="-1"
        with self.assertRaises(ValueError):self.convert(row)
    def test_nonfinite_price_rejected(self):
        for bad in ("nan","inf","1e309"):
            row=list(self.row);row[1]=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.convert(row)
    def test_negative_and_zero_price_rejected(self):
        for bad in ("-1","0"):
            row=list(self.row);row[4]=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.convert(row)
    def test_inconsistent_high_low_rejected(self):
        for index,bad in ((2,"100"),(3,"101")):
            row=list(self.row);row[index]=bad
            with self.subTest(index=index),self.assertRaises(ValueError):self.convert(row)
    def test_boolean_price_and_volume_rejected(self):
        for index in (1,5):
            row=list(self.row);row[index]=True
            with self.subTest(index=index),self.assertRaises(ValueError):self.convert(row)
    def test_missing_fields_rejected(self):
        with self.assertRaises(ValueError):self.convert(self.row[:4])
    def test_newest_unclosed_bar_excluded(self):
        last=list(self.last);last[1]="nan"
        self.assertEqual(len(self.convert(self.row)),1)
        self.assertEqual(len(convert_closed_candles({"candles":[self.row,last]})),1)
if __name__=="__main__":unittest.main()
