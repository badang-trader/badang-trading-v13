"""Divergence pivot behavior and exact scan failure context."""
import unittest
from unittest.mock import patch
import app

class DivergenceTests(unittest.TestCase):
    def test_bullish_lower_low_higher_rsi(self):
        p=[12]*35;r=[50]*35
        p[9]=5;p[24]=4
        r[9]=25;r[24]=38
        with patch.object(app,"pivots",side_effect=lambda values,low=True,w=3:[9,24] if low else []):
            self.assertEqual(app.divergence(p,r),"bullish")
    def test_bearish_higher_high_lower_rsi(self):
        p=[10]*35;r=[50]*35
        p[9]=18;p[24]=20
        r[9]=75;r[24]=60
        with patch.object(app,"pivots",side_effect=lambda values,low=True,w=3:[] if low else [9,24]):
            self.assertEqual(app.divergence(p,r),"bearish")
    def test_no_divergence_on_flat(self):
        self.assertEqual(app.divergence([10]*35,[50]*35),"none")
    def test_flat_rsi_is_neutral(self):
        self.assertEqual(app.rsi([100.0]*30),50.0)
    def test_rising_rsi_is_100(self):
        self.assertEqual(app.rsi(list(range(1,31))),100.0)
    def test_falling_rsi_is_zero(self):
        self.assertEqual(app.rsi(list(range(31,1,-1))),0.0)
    def test_plateau_does_not_create_false_pivots(self):
        self.assertEqual(app.pivots([10.0]*35,low=True),[])
        self.assertEqual(app.pivots([10.0]*35,low=False),[])
    def test_unique_swing_pivot_is_detected(self):
        values=[10.0]*35
        values[16]=4.0
        self.assertEqual(app.pivots(values,low=True),[16])
    def test_divergence_on_flat_market_is_none(self):
        self.assertEqual(app.divergence([10.0]*35,[50.0]*35),"none")
    def test_insufficient_history_names_symbol_and_frame(self):
        def analyze(symbol,frame):
            if frame=="1D":
                raise ValueError("Bitget 연속 확정봉 부족: 89개 / 최소 205개")
            return {"trend":"UP"}
        with patch.object(app,"analyze",side_effect=analyze):
            with self.assertRaisesRegex(ValueError,r"BTCUSDT 1D: .*89개"):
                app.scan_one("BTCUSDT","swing")

if __name__=="__main__":unittest.main()
