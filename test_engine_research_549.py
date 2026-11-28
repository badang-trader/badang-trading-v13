"""Historical analysis adapter cannot see future candles."""
import unittest
from unittest.mock import patch
import badang_engine_research_549 as m

class EngineResearchTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100+i*.01,"high":101+i*.01,"low":99+i*.01,
                    "close":100+i*.01,"volume":100} for i in range(215)]
    def test_each_analysis_receives_only_past_prefix(self):
        lengths=[]
        def engine(prefix,mode):
            lengths.append(len(prefix))
            return {"status":"ok","recommendation":"LONG" if len(prefix)==205 else "WAIT"}
        with patch.object(m,"analyze",side_effect=engine):
            signals=m.research_engine_signals(self.bars)
        self.assertEqual(lengths,list(range(205,216)))
        self.assertEqual(signals,[{"signal_index":204,"direction":"long"}])
    def test_engine_signal_is_evaluated_at_next_open(self):
        def engine(prefix,mode):
            return {"status":"ok","recommendation":"SHORT" if len(prefix)==205 else "WAIT"}
        with patch.object(m,"analyze",side_effect=engine):
            result=m.research_engine_backtest(self.bars,horizon=3,fee_per_side=0,slippage_per_side=0)
        self.assertEqual(result["summary"]["trades"],1)
        self.assertEqual(result["trades"][0]["entry_index"],205)
        self.assertEqual(result["trades"][0]["exit_index"],208)
    def test_unclosed_future_exit_is_not_invented(self):
        with patch.object(m,"analyze",return_value={"status":"ok","recommendation":"LONG"}):
            result=m.research_engine_backtest(self.bars,horizon=3)
        self.assertTrue(all(t["exit_index"]<len(self.bars) for t in result["trades"]))
    def test_invalid_historical_analysis_rejected(self):
        with patch.object(m,"analyze",return_value={"status":"invalid_data","recommendation":"WAIT"}):
            with self.assertRaisesRegex(ValueError,"Historical analysis invalid"):
                m.research_engine_signals(self.bars)
if __name__=="__main__":unittest.main()
