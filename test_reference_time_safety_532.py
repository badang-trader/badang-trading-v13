"""Signal timestamp must not fall back to unrelated metadata on invalid candle."""
import unittest
from app import get_reference_time

class ReferenceTimeSafetyTests(unittest.TestCase):
    def test_valid_candle_is_authoritative(self):
        self.assertEqual(get_reference_time({"timestamp":999},[[1700000000000,1]]),1700000000000)
    def test_invalid_candle_does_not_fallback(self):
        for value in (float("nan"),float("inf"),float("-inf"),0,-1,"oops"):
            with self.subTest(value=str(value)):
                self.assertIsNone(get_reference_time({"timestamp":1700000000000},[[value,1]]))
    def test_empty_supplied_history_does_not_fallback(self):
        self.assertIsNone(get_reference_time({"timestamp":1700000000000},[]))
    def test_metadata_fallback_when_no_candle_data_supplied(self):
        self.assertEqual(get_reference_time({"timestamp":1700000000000}),1700000000000)

if __name__=="__main__":unittest.main()
