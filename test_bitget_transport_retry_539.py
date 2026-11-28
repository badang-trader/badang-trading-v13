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

    def test_connection_error_then_success(self):
        good=Mock(status_code=200)
        good.json.return_value={"code":"00000","data":[["1","2"]]}
        with patch.object(m.SESSION,"get",side_effect=[requests.exceptions.ConnectionError("disconnect"),good]) as get,patch.object(m.time,"sleep"):
            self.assertEqual(m._get("/test",{}),[["1","2"]])
            self.assertEqual(get.call_count,2)
    def test_permanent_connection_error_fails_closed(self):
        with patch.object(m.SESSION,"get",side_effect=requests.exceptions.ConnectionError("disconnect")) as get,patch.object(m.time,"sleep"):
            with self.assertRaises(requests.exceptions.ConnectionError):
                m._get("/test",{})
            self.assertEqual(get.call_count,3)

    def test_retry_backoff_does_not_hold_request_lock(self):
        good=Mock(status_code=200)
        good.json.return_value={"code":"00000","data":[]}
        observed=[]
        def record_sleep(seconds):
            if seconds>=0.8:
                acquired=m._REQUEST_LOCK.acquire(blocking=False)
                observed.append(acquired)
                if acquired:
                    m._REQUEST_LOCK.release()
        with patch.object(m.SESSION,"get",side_effect=[requests.exceptions.ReadTimeout("timeout"),good]),patch.object(m.time,"sleep",side_effect=record_sleep):
            m._get("/test",{})
        self.assertEqual(observed,[True])

if __name__=="__main__":unittest.main()
