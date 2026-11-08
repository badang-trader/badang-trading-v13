"""Divergence pivot behavior and exact scan failure context."""
import unittest
from unittest.mock import patch
import app

class DivergenceTests(unittest.TestCase):
    def test_bullish_lower_low_higher_rsi(self):
        p=[12]*35;r=[50]*35
        p[9]=5;p[24]=4
        r[9]=25;r[24]=38
        self.assertEqual(app.divergence(p,r),"bullish")
    def test_bearish_higher_high_lower_rsi(self):
        p=[10]*35;r=[50]*35
        p[9]=18;p[24]=20
        r[9]=75;r[24]=60
        self.assertEqual(app.divergence(p,r),"bearish")
    def test_no_divergence_on_flat(self):
        self.assertEqual(app.divergence([10]*35,[50]*35),"none")
    def test_insufficient_history_names_symbol_and_frame(self):
        def analyze(symbol,frame):
            if frame=="1D":
                raise ValueError("Bitget 연속 확정봉 부족: 89개 / 최소 205개")
            return {"trend":"UP"}
        with patch.object(app,"analyze",side_effect=analyze):
            with self.assertRaisesRegex(ValueError,r"BTCUSDT 1D: .*89개"):
                app.scan_one("BTCUSDT","swing")

if __name__=="__main__":unittest.main()
