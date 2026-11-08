"""Scan API must reject malformed turnover filters before exchange requests."""
import unittest
from unittest.mock import patch
from app import app

class ScanInputSafetyTests(unittest.TestCase):
    def test_invalid_turnover_returns_400_without_exchange_call(self):
        for value in ("nan","inf","-inf","-1","oops","1e9999"):
            with self.subTest(value=value),patch("app.symbols") as symbols:
                response=app.test_client().get("/api/scan",query_string={"min_turnover":value})
                self.assertEqual(response.status_code,400)
                symbols.assert_not_called()
    def test_valid_turnover_reaches_symbol_discovery(self):
        with patch("app.symbols",return_value=[]) as symbols:
            response=app.test_client().get("/api/scan",query_string={"min_turnover":"1000000"})
            self.assertEqual(response.status_code,200)
            symbols.assert_called_once_with(1000000.0)

if __name__=="__main__":unittest.main()
