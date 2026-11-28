"""Reject malformed historical exchange snapshots without reaching research."""
import unittest
from unittest.mock import patch
import badang_live_historical_research_551 as m

class SnapshotShapeTests(unittest.TestCase):
    def test_non_mapping_snapshot_rejected(self):
        for value in (None,[],123,"bad"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                m.convert_closed_candles(value)
    def test_missing_or_invalid_candles_rejected(self):
        for value in ({},{"candles":None},{"candles":"bad"},{"candles":{}},{"candles":()}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                m.convert_closed_candles(value)
    def test_empty_or_only_open_candle_rejected(self):
        for value in ([],[["1793999700000","100","102","99","101","10"]]):
            with self.subTest(value=value),self.assertRaises(ValueError):
                m.convert_closed_candles({"candles":value})
    def test_invalid_snapshot_does_not_reach_engine(self):
        with patch.object(m,"fastest_candles",return_value={"candles":None}),patch.object(m,"research_engine_backtest") as engine:
            with self.assertRaises(ValueError):m.main()
            engine.assert_not_called()
    def test_two_candles_yield_one_confirmed_candle(self):
        row=["1793999700000","100","102","99","101","10"]
        result=m.convert_closed_candles({"candles":[row,["1794000600000","100","102","99","101","10"]]})
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["close"],101)
if __name__=="__main__":unittest.main()
