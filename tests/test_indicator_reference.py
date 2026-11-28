"""Independent EMA/RSI reference checks and invalid-history guards."""
import unittest
from app import ema, rsi

class IndicatorReferenceTests(unittest.TestCase):
    def test_ema_reference_recursive(self):
        prices=[10.,12.,11.,15.,14.]
        alpha=2/4
        expected=[prices[0]]
        for price in prices[1:]:
            expected.append(alpha*price+(1-alpha)*expected[-1])
        for actual,reference in zip(ema(prices,3),expected):
            self.assertAlmostEqual(actual,reference,places=12)

    def test_rsi_monotonic_rise(self):
        self.assertEqual(rsi(list(range(20)),14),100.0)

    def test_rsi_monotonic_fall(self):
        self.assertAlmostEqual(rsi(list(range(20,0,-1)),14),0.0)

    def test_rsi_flat(self):
        self.assertEqual(rsi([100.]*20,14),50.0)

    def test_short_rsi_history_rejected(self):
        with self.assertRaises(ValueError):
            rsi([100.]*14,14)

    def test_empty_ema_rejected(self):
        with self.assertRaises(ValueError):
            ema([],20)

    def test_invalid_ema_period_rejected(self):
        with self.assertRaises(ValueError):
            ema([100.],0)

if __name__=='__main__':
    unittest.main()
