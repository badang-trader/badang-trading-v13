"""Transient Bitget transport failures retry without stale-data fallback."""
import unittest
from unittest.mock import patch,Mock
import requests
import bitget_market_data as m

class TransportRetryTests(unittest.TestCase):
    def setUp(self):
        m._LAST_REQUEST[0]=0
    def test_timeout_then_success(self):
        good=Mock(status_code=200)
        good.json.return_value={"code":"00000","data":[["1","2"]]}
        with patch.object(m.SESSION,"get",side_effect=[requests.exceptions.ReadTimeout("timeout"),good]) as get,patch.object(m.time,"sleep"):
            self.assertEqual(m._get("/test",{}),[["1","2"]])
            self.assertEqual(get.call_count,2)
    def test_three_timeouts_fail_closed(self):
        with patch.object(m.SESSION,"get",side_effect=requests.exceptions.ReadTimeout("timeout")) as get,patch.object(m.time,"sleep"):
            with self.assertRaises(requests.exceptions.ReadTimeout):
                m._get("/test",{})
            self.assertEqual(get.call_count,3)

if __name__=="__main__":unittest.main()
