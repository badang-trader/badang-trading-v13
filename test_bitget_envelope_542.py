"""Bitget API response envelopes fail closed without breaking dict snapshots."""
import unittest
from unittest.mock import Mock,patch
import bitget_market_data as m

class BitgetEnvelopeTests(unittest.TestCase):
    def check(self,payload):
        response=Mock(status_code=200)
        response.json.return_value=payload
        with patch.object(m.SESSION,"get",return_value=response),patch.object(m.time,"sleep"):
            return m._get("/test",{})
    def test_non_object_envelope_rejected(self):
        with self.assertRaisesRegex(ValueError,"응답 구조"):
            self.check([])
    def test_missing_data_rejected(self):
        with self.assertRaisesRegex(ValueError,"데이터 누락"):
            self.check({"code":"00000"})
    def test_dictionary_snapshot_remains_supported(self):
        self.assertEqual(self.check({"code":"00000","data":{"openInterest":"42"}}),{"openInterest":"42"})
    def test_empty_candle_list_remains_supported(self):
        self.assertEqual(self.check({"code":"00000","data":[]}),[])

if __name__=="__main__":unittest.main()
