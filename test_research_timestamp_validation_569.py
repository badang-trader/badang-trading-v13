"""Timestamped historical candles must be contiguous, unique and on-grid."""
import unittest
from badang_research_timestamp_validation_569 import validate_research_timestamps as validate

class TimestampSequenceTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"timestamp":i*900000} for i in range(20)]
    def test_valid_contiguous_series(self):
        self.assertTrue(validate(self.bars,900000))
    def test_duplicate_timestamp_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[5]["timestamp"]=bars[4]["timestamp"]
        with self.assertRaises(ValueError):
            validate(bars,900000)
    def test_missing_interval_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[5]["timestamp"]+=900000
        with self.assertRaises(ValueError):
            validate(bars,900000)
    def test_reversed_timestamp_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[5],bars[6]=bars[6],bars[5]
        with self.assertRaises(ValueError):
            validate(bars,900000)
    def test_off_grid_timestamp_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[5]["timestamp"]+=1
        with self.assertRaises(ValueError):
            validate(bars,900000)
    def test_bad_interval_and_boolean_timestamp_rejected(self):
        for interval in (0,-1,True):
            with self.assertRaises(ValueError):
                validate(self.bars,interval)
        bars=[dict(b) for b in self.bars]
        bars[5]["timestamp"]=True
        with self.assertRaises(ValueError):
            validate(bars,900000)
if __name__=="__main__":unittest.main()
