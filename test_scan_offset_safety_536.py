"""Scan pagination must not silently reset malformed offsets."""
import unittest
from unittest.mock import patch
from app import app

class ScanOffsetSafetyTests(unittest.TestCase):
    def test_invalid_offset_rejected_without_scanning(self):
        for value in ("nan","inf","-1","oops","1.5"):
            with self.subTest(value=value),patch("app.symbols",return_value=[]) as symbols,patch("app.scan_one") as scan_one:
                response=app.test_client().get("/api/scan",query_string={"offset":value})
                self.assertEqual(response.status_code,400)
                symbols.assert_not_called()
                scan_one.assert_not_called()
    def test_valid_offset_kept(self):
        with patch("app.symbols",return_value=[]) as symbols:
            response=app.test_client().get("/api/scan",query_string={"offset":"3"})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.get_json()["offset"],3)

if __name__=="__main__":unittest.main()
