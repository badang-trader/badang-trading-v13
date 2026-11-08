"""Research signal decisions must be prefix-causal and executable."""
import unittest
from unittest.mock import patch
import badang_engine_research_549 as engine

class ResearchFutureLeakageTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100,"high":101,"low":99,"close":100,"volume":1} for _ in range(215)]
    def fake_analyze(self,prefix,mode):
        return {"status":"ok","recommendation":"LONG" if len(prefix)%2 else "SHORT"}
    def test_future_suffix_cannot_rewrite_past_signal_decisions(self):
        with patch.object(engine,"analyze",side_effect=self.fake_analyze):
            original=engine.research_engine_signals(self.bars,end_index=210)
            changed=[dict(x) for x in self.bars]
            changed[212]["close"]=10000
            changed[213]["close"]=1
            altered=engine.research_engine_signals(changed,end_index=210)
        self.assertEqual(original,altered)
    def test_backtest_does_not_analyze_unexecutable_tail(self):
        seen=[]
        def fake(prefix,mode):
            seen.append(len(prefix))
            return {"status":"ok","recommendation":"LONG"}
        with patch.object(engine,"analyze",side_effect=fake):
            result=engine.research_engine_backtest(self.bars,horizon=4)
        self.assertEqual(max(seen),210)
        self.assertTrue(all(t["exit_index"]<len(self.bars) for t in result["trades"]))
    def test_horizon_longer_than_history_yields_no_trades(self):
        with patch.object(engine,"analyze") as mock:
            result=engine.research_engine_backtest(self.bars,horizon=1000)
        mock.assert_not_called()
        self.assertEqual(result["trades"],[])
    def test_cutoff_boolean_and_overflow_rejected(self):
        for cutoff in (True,-1,len(self.bars)+1):
            with self.subTest(cutoff=cutoff),self.assertRaises(ValueError):
                engine.research_engine_signals(self.bars,end_index=cutoff)
    def test_invalid_horizon_rejected_before_analysis(self):
        for horizon in (0,-1,True,1.5):
            with self.subTest(horizon=horizon),self.assertRaises(ValueError):
                engine.research_engine_backtest(self.bars,horizon=horizon)
if __name__=="__main__":unittest.main()
