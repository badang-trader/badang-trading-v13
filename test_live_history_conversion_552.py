"""Guard against Bitget array/ledger mapping regression."""
import unittest
from badang_live_historical_research_551 import convert_closed_candles
from badang_research_backtest_545 import evaluate_signal

class LiveHistoryConversionTests(unittest.TestCase):
    def test_named_ohlc_and_unclosed_bar_excluded(self):
        snapshot={"candles":[
            ["1000","100","101","99","100.5","5"],
            ["2000","101","103","100","102","6"],
            ["3000","103","104","102","103.5","7"],
            ["4000","104","105","103","104.5","8"],
            ["5000","999","1000","998","999","1"]]}
        rows=convert_closed_candles(snapshot)
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[1]["open"],101)
        self.assertEqual(rows[3]["close"],104.5)
        trade=evaluate_signal(rows,0,"long",horizon=2,fee_per_side=0,slippage_per_side=0)
        self.assertEqual(trade["actual_entry"],101)
        self.assertEqual(trade["actual_exit"],104.5)
if __name__=="__main__":unittest.main()
