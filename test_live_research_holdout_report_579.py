"""Integration: live historical report must separate development and holdout."""
import unittest
from unittest.mock import patch
import io,json
from contextlib import redirect_stdout
import badang_live_historical_research_551 as m

BASE=1793999700000
def snapshot(frame):
    step=900000 if frame=="15m" else 86400000
    start=BASE if frame=="15m" else BASE-BASE%86400000
    row=lambda i:[str(start+i*step),"100","102","99","101","10"]
    return {"candles":[row(i) for i in range(212)]}

class LiveHoldoutReportTests(unittest.TestCase):
    def test_public_report_has_separate_unverified_holdout(self):
        def market(symbol,frame):
            return snapshot(frame)
        with patch.object(m,"fastest_candles",side_effect=market),patch.object(m,"research_engine_backtest",return_value={"trades":[],"summary":None,"skipped_overlaps":0}):
            output=io.StringIO()
            with redirect_stdout(output):m.main()
        report=json.loads(output.getvalue().split("LIVE_HISTORICAL_RESEARCH_SUMMARY ",1)[1])
        self.assertFalse(report["trading_enabled"])
        self.assertEqual(len(report["results"]),2)
        for result in report["results"]:
            holdout=result["chronological_holdout"]
            self.assertEqual(holdout["split_index"],int(result["confirmed_bars"]*.7))
            self.assertEqual(holdout["development"]["completed_trades"],0)
            self.assertIsNone(holdout["holdout"]["metrics"])
            self.assertFalse(holdout["performance_verified"])
if __name__=="__main__":unittest.main()
