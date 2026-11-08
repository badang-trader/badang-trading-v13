"""Malformed timestamp order must fail before the historical research engine runs."""
import unittest
from unittest.mock import patch
import badang_live_historical_research_551 as m

BASE=1794000000000
STEP=900000

def candle(ts):
    return [str(ts),"100","102","99","101","10"]

class LiveResearchOrderingTests(unittest.TestCase):
    def check_rejected(self,times):
        snapshot={"candles":[candle(t) for t in times]+[candle(times[-1]+STEP)]}
        with patch.object(m,"fastest_candles",return_value=snapshot),patch.object(m,"research_engine_backtest") as engine:
            with self.assertRaises(ValueError):m.main()
            engine.assert_not_called()
    def test_duplicate_closed_timestamp_rejected_before_engine(self):
        self.check_rejected([BASE,BASE+STEP,BASE+STEP])
    def test_reversed_closed_timestamp_rejected_before_engine(self):
        self.check_rejected([BASE+STEP,BASE])
    def test_missing_closed_interval_rejected_before_engine(self):
        self.check_rejected([BASE,BASE+STEP*2])
    def test_off_grid_closed_timestamp_rejected_before_engine(self):
        self.check_rejected([BASE+1,BASE+STEP+1])
    def test_normal_sequence_still_passes_timestamp_validation(self):
        rows=m.convert_closed_candles({"candles":[candle(BASE),candle(BASE+STEP),candle(BASE+2*STEP)]})
        self.assertTrue(m.validate_research_timestamps(rows,STEP))
        self.assertEqual(len(rows),2)
if __name__=="__main__":unittest.main()
