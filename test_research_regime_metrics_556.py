"""Grouped regime statistics are conditional, not an account equity curve."""
import unittest
from badang_research_regime_metrics_556 import summarize_by_regime

class RegimeMetricsTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"close":100} for _ in range(60)]
        self.bars[25]["close"]=110
        self.bars[30]["close"]=90
        self.bars[35]["close"]=100
    def test_regime_trade_counts_and_returns(self):
        trades=[{"signal_index":25,"entry_index":26,"exit_index":27,"net_return":0.1},
                {"signal_index":30,"entry_index":31,"exit_index":32,"net_return":-0.2},
                {"signal_index":35,"entry_index":36,"exit_index":37,"net_return":0.01}]
        result=summarize_by_regime(self.bars,trades)
        self.assertEqual([result[k]["trade_count"] for k in ("up","down","sideways")],[1,1,1])
        self.assertAlmostEqual(result["up"]["metrics"]["compounded_net_return"],0.1)
        self.assertAlmostEqual(result["down"]["metrics"]["compounded_net_return"],-0.2)
        self.assertTrue(all(x["conditional_only_not_portfolio"] for x in result.values()))
    def test_empty_group_not_reported_as_profitable(self):
        result=summarize_by_regime(self.bars,[])
        self.assertTrue(all(x["metrics"] is None for x in result.values()))
    def test_future_candles_do_not_change_past_regimes(self):
        trades=[{"signal_index":25,"entry_index":26,"exit_index":27,"net_return":0.1}]
        a=summarize_by_regime(self.bars,trades)
        b=summarize_by_regime(self.bars+[{"close":999999}],trades)
        self.assertEqual(a,b)
if __name__=="__main__":unittest.main()
