"""Equivalent candle formatting must not masquerade as a data conflict."""
import unittest
from unittest.mock import patch
from bitget_market_data import fastest_candles

class DuplicateFormattingTests(unittest.TestCase):
    def _run(self, conflict):
        step=900000
        now=1760000000000
        current=(now//step)*step
        candles=[[str(current-i*step),"100","101","99","100","10"] for i in range(220)]
        duplicate=[str(current-10*step),"100.0","101.00","99.0","100.000","10.0"]
        if conflict:
            duplicate[4]="100.5"
        candles.append(duplicate)
        with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",return_value=candles):
            return fastest_candles("BTCUSDT","15m")
    def test_equivalent_numeric_format_is_accepted(self):
        result=self._run(False)
        self.assertGreaterEqual(len(result["candles"]),206)
    def test_conflicting_duplicate_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            self._run(True)

    def test_duplicate_nonfinite_values_rejected(self):
        step=900000
        now=1760000000000
        current=(now//step)*step
        candles=[[str(current-i*step),"100","101","99","100","10"] for i in range(220)]
        candles.append([str(current-10*step),"100","101","99","nan","10"])
        with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",return_value=candles):
            with self.assertRaisesRegex(ValueError,"Conflicting"):
                fastest_candles("BTCUSDT","15m")

if __name__=="__main__":unittest.main()
