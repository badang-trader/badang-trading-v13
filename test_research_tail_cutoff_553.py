"""Ensure incomplete trailing signal windows are never analyzed or traded."""
import unittest
from unittest.mock import patch
import badang_engine_research_549 as m

class ResearchTailCutoffTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100,"high":101,"low":99,"close":100,"volume":1} for _ in range(215)]
    def test_no_future_window_means_no_engine_invocation(self):
        with patch.object(m,"analyze") as engine:
            result=m.research_engine_backtest(self.bars,horizon=11)
        engine.assert_not_called()
        self.assertEqual(result["trades"],[])
        self.assertIsNone(result["summary"])
    def test_last_unexecutable_signals_not_analyzed(self):
        seen=[]
        def fake(prefix,mode):
            seen.append(len(prefix))
            return {"status":"ok","recommendation":"LONG"}
        with patch.object(m,"analyze",side_effect=fake):
            result=m.research_engine_backtest(self.bars,horizon=3)
        self.assertEqual(seen,list(range(205,212)))
        self.assertLess(result["trades"][-1]["exit_index"],len(self.bars))
    def test_explicit_cutoff_rejects_invalid_inputs(self):
        for value in (-1,216,True,2.5):
            with self.subTest(value=value),self.assertRaises(ValueError):
                m.research_engine_signals(self.bars,end_index=value)
if __name__=="__main__":unittest.main()
