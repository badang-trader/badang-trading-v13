"""Scan API must expose insufficient-history honestly and isolate symbol failures."""
import unittest
from unittest.mock import patch
import app

class ScanFailureIsolationTests(unittest.TestCase):
    def test_missing_history_is_not_a_candidate(self):
        def scanner(sym, mode):
            if sym=="NEWUSDT":
                raise ValueError("Bitget 연속 확정봉 부족: 89개 / 최소 205개")
            return {"symbol":sym,"signal":"WAIT","mode":mode}
        with patch.object(app,"symbols",return_value=[("NEWUSDT",100),("BTCUSDT",99)]),patch.object(app,"scan_one",side_effect=scanner):
            with app.app.test_client() as client:
                response=client.get("/api/scan?mode=swing")
        self.assertEqual(response.status_code,200)
        body=response.get_json()
        self.assertEqual(len(body["results"]),1)
        self.assertEqual(body["results"][0]["symbol"],"BTCUSDT")
        self.assertEqual(len(body["errors"]),1)
        self.assertEqual(body["errors"][0]["symbol"],"NEWUSDT")
        self.assertIn("확정봉 부족",body["errors"][0]["error"])
        self.assertEqual(body["recommendations"],[])

    def test_bad_turnover_fails_with_400(self):
        with app.app.test_client() as client:
            response=client.get("/api/scan?min_turnover=not-a-number")
        self.assertEqual(response.status_code,400)

if __name__=="__main__":unittest.main()
