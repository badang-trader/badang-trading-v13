"""Deterministic tests for bounded Bitget 429 handling."""
import unittest
from unittest.mock import patch
import bitget_market_data as b

class FakeResponse:
    def __init__(self,status,headers=None):
        self.status_code=status
        self.headers=headers or {}
    def raise_for_status(self):
        if self.status_code>=400: raise RuntimeError("HTTP "+str(self.status_code))
    def json(self):return {"code":"00000","data":[["ok"]]}

class RetryTests(unittest.TestCase):
    def test_rate_limit_then_success(self):
        with patch.object(b.SESSION,"get",side_effect=[FakeResponse(429),FakeResponse(200)]) as get,patch.object(b.time,"sleep"):
            self.assertEqual(b._get("/test",{}),[["ok"]])
        self.assertEqual(get.call_count,2)
    def test_rate_limit_is_bounded(self):
        with patch.object(b.SESSION,"get",return_value=FakeResponse(429)) as get,patch.object(b.time,"sleep"):
            with self.assertRaisesRegex(ValueError,"429"):
                b._get("/test",{})
        self.assertEqual(get.call_count,3)
    def test_non_rate_limit_error_not_silently_retried(self):
        with patch.object(b.SESSION,"get",return_value=FakeResponse(400)) as get:
            with self.assertRaises(RuntimeError):
                b._get("/test",{})
        self.assertEqual(get.call_count,1)

if __name__=="__main__":unittest.main()
