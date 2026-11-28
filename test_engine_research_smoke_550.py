"""End-to-end deterministic research smoke checks using the unmocked engine."""
import unittest
from badang_engine_research_549 import research_engine_signals,research_engine_backtest

def candles(n=225):
    # Valid OHLCV, gently rising market with periodic confirmed swings.
    out=[]
    for i in range(n):
        center=100+i*.09+((i%13)-6)*.16
        out.append({"open":center-.1,"high":center+.7,"low":center-.7,
                    "close":center+.1,"volume":100+i%11})
    return out

class RealEngineResearchSmokeTests(unittest.TestCase):
    def test_real_engine_historical_signals_are_causal_and_valid(self):
        bars=candles()
        signals=research_engine_signals(bars)
        self.assertTrue(all(204<=s["signal_index"]<len(bars) for s in signals))
        self.assertTrue(all(s["direction"] in ("long","short") for s in signals))
        self.assertEqual(signals,research_engine_signals(bars))
    def test_real_engine_backtest_has_only_closed_nonoverlapping_trades(self):
        bars=candles()
        result=research_engine_backtest(bars,horizon=3)
        trades=result["trades"]
        for t in trades:
            self.assertEqual(t["entry_index"],t["signal_index"]+1)
            self.assertEqual(t["exit_index"],t["entry_index"]+3)
            self.assertLess(t["exit_index"],len(bars))
        for a,b in zip(trades,trades[1:]):
            self.assertLess(a["exit_index"],b["entry_index"])
        if trades:
            self.assertEqual(result["summary"]["trades"],len(trades))
        else:
            self.assertIsNone(result["summary"])
    def test_future_append_does_not_change_historical_signals(self):
        bars=candles()
        original=research_engine_signals(bars)
        extended=research_engine_signals(bars+candles(10))
        self.assertEqual(original,[s for s in extended if s["signal_index"]<len(bars)])
if __name__=="__main__":unittest.main()
