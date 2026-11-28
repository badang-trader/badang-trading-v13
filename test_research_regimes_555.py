"""Causal regime labels must not depend on future bars."""
import unittest
from badang_research_regimes_555 import regime_at

class MarketRegimeTests(unittest.TestCase):
    def test_up_down_sideways(self):
        def bars(a,b):
            return [{"close":a}]+[{"close":a} for _ in range(19)]+[{"close":b}]
        self.assertEqual(regime_at(bars(100,110),20),"up")
        self.assertEqual(regime_at(bars(100,90),20),"down")
        self.assertEqual(regime_at(bars(100,101),20),"sideways")
    def test_future_append_does_not_change_regime(self):
        bars=[{"close":100+i} for i in range(40)]
        original=regime_at(bars,25)
        self.assertEqual(original,regime_at(bars+[{"close":99999}],25))
    def test_invalid_input_rejected(self):
        bars=[{"close":100} for _ in range(25)]
        for kwargs in ({"signal_index":19},{"signal_index":25},
                       {"signal_index":20,"lookback":0},
                       {"signal_index":20,"threshold":float("nan")}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                regime_at(bars,**kwargs)
if __name__=="__main__":unittest.main()
