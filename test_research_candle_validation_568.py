"""Research OHLC input corruption and full-sequence validation."""
import unittest
from badang_research_candle_validation_568 import validate_research_candles
from badang_research_runner_548 import evaluate_signals

class ResearchCandleValidationTests(unittest.TestCase):
    def setUp(self):
        self.bars=[{"open":100,"high":102,"low":99,"close":101} for _ in range(40)]
    def test_valid_ohlc_accepted(self):
        self.assertTrue(validate_research_candles(self.bars))
    def test_high_below_close_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[10]["high"]=100
        with self.assertRaisesRegex(ValueError,"Inconsistent"):
            evaluate_signals(bars,[{"signal_index":20,"direction":"long"}])
    def test_low_above_open_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[12]["low"]=101
        with self.assertRaisesRegex(ValueError,"Inconsistent"):
            validate_research_candles(bars)
    def test_invalid_untraded_candle_rejected(self):
        bars=[dict(b) for b in self.bars]
        bars[38]["close"]=float("nan")
        with self.assertRaises(ValueError):
            evaluate_signals(bars,[{"signal_index":20,"direction":"long"}])
    def test_half_missing_high_low_rejected(self):
        bars=[dict(b) for b in self.bars]
        del bars[3]["high"]
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            validate_research_candles(bars)
    def test_minimal_open_close_test_fixture_supported(self):
        self.assertTrue(validate_research_candles([{"open":100,"close":101}]))
if __name__=="__main__":unittest.main()
