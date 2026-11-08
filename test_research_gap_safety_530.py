"""Invalid interior candles must not be silently joined into fake adjacent bars."""
import unittest
from badang_analysis_v13 import analyze

class GapSafetyTests(unittest.TestCase):
    def test_invalid_middle_candle_fails_closed(self):
        rows=[[i,100,102,99,101,10] for i in range(230)]
        rows[110][4]=float("nan")
        result=analyze(rows,symbol="TESTUSDT")
        self.assertEqual(result["status"],"invalid_data")
        self.assertEqual(result["recommendation"],"WAIT")
        self.assertEqual(result["rejected_candles"],1)
    def test_invalid_first_candle_fails_closed(self):
        rows=[[i,100,102,99,101,10] for i in range(230)]
        rows[0][1]=0
        result=analyze(rows)
        self.assertEqual(result["status"],"invalid_data")
        self.assertEqual(result["recommendation"],"WAIT")
    def test_clean_history_is_not_flagged_invalid(self):
        rows=[[i,100,102,99,101,10] for i in range(230)]
        self.assertEqual(analyze(rows)["status"],"ok")

if __name__=="__main__":unittest.main()
