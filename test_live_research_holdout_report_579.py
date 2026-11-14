"""Integration: live historical report must separate development and holdout."""
import unittest
from unittest.mock import patch
import io,json
from contextlib import redirect_stdout
import badang_live_historical_research_551 as m

BASE=1793999700000
def snapshot(frame):
    step=m.FRAME_INTERVAL_MS[frame]
    start=BASE-BASE%step
    row=lambda i:[str(start+i*step),"100","102","99","101","10"]
    return {"candles":[row(i) for i in range(212)]}

class LiveHoldoutReportTests(unittest.TestCase):
    def test_public_report_has_separate_unverified_holdout(self):
        def market(symbol,frame):
            return snapshot(frame)
        with patch.object(m,"fastest_candles",side_effect=market),patch.object(m,"research_engine_backtest",return_value={"trades":[],"summary":None,"skipped_overlaps":0}),patch.object(m,"chronological_support_holdout",return_value={"status":"ok","trading_ready":False}) as support_mock:
            output=io.StringIO()
            with redirect_stdout(output):m.main()
        report=json.loads(output.getvalue().split("LIVE_HISTORICAL_RESEARCH_SUMMARY ",1)[1])
        self.assertFalse(report["trading_enabled"])
        self.assertEqual(len(report["results"]),len(m.TARGETS))
        self.assertEqual(support_mock.call_count,8)
        self.assertEqual({call.args[1] for call in support_mock.call_args_list},{"BTC","ETH"})
        for result in report["results"]:
            self.assertLess(result["research_window_start_ms"], result["research_window_end_ms"])
            self.assertFalse(result["mode_specific_strategy_verified"])
            self.assertEqual(result["mode_comparison_warning"], "SCALP_SWING_SHARE_SIGNAL_RULES_AND_HORIZON")
            if (result["symbol"],result["frame"],result["mode"]) in (("BTCUSDT","15m","scalp"),("BTCUSDT","30m","scalp"),("BTCUSDT","1H","scalp"),("BTCUSDT","4H","swing"),("ETHUSDT","15m","scalp"),("ETHUSDT","30m","scalp"),("ETHUSDT","1H","scalp"),("ETHUSDT","4H","swing")):
                self.assertFalse(result["support_holdout_research"]["trading_ready"])
            else:
                self.assertIsNone(result["support_holdout_research"])
            holdout=result["chronological_holdout"]
            self.assertEqual(holdout["split_index"],int(result["confirmed_bars"]*.7))
            self.assertEqual(holdout["development"]["completed_trades"],0)
            self.assertIsNone(holdout["holdout"]["metrics"])
            self.assertFalse(holdout["performance_verified"])
if __name__=="__main__":unittest.main()
