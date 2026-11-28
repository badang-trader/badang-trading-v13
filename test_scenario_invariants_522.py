"""Deterministic long/short scenario invariants; no market or order access."""
import math
import unittest
import app

class ScenarioInvariantTests(unittest.TestCase):
    def setup(self, price=100.0, atr=2.0, low=96.0, high=104.0):
        return {"price":price,"atr":atr,"swing_low":low,"swing_high":high}
    def test_long_stop_and_targets(self):
        for mode,rr in (("scalp",1.5),("swing",2.0)):
            p=app.scenario(self.setup(),"LONG",mode)
            self.assertIsNotNone(p)
            self.assertLess(p["stop"],p["entry"])
            self.assertLess(p["entry"],p["tp1"])
            self.assertLess(p["tp1"],p["tp2"])
            self.assertAlmostEqual((p["tp1"]-p["entry"])/(p["entry"]-p["stop"]),rr)
    def test_short_stop_and_targets(self):
        for mode,rr in (("scalp",1.5),("swing",2.0)):
            p=app.scenario(self.setup(),"SHORT",mode)
            self.assertIsNotNone(p)
            self.assertGreater(p["stop"],p["entry"])
            self.assertGreater(p["entry"],p["tp1"])
            self.assertGreater(p["tp1"],p["tp2"])
            self.assertAlmostEqual((p["entry"]-p["tp1"])/(p["stop"]-p["entry"]),rr)
    def test_rejects_invalid_and_excessive_risk(self):
        for setup in (self.setup(atr=0),self.setup(price=0),self.setup(low=50,high=150)):
            self.assertIsNone(app.scenario(setup,"LONG","swing"))
            self.assertIsNone(app.scenario(setup,"SHORT","swing"))
    def test_scores_are_bounded(self):
        setup={"trend":"UP","rsi":60,"volume_ratio":1.2,"fake_breakout":False,"divergence":"none"}
        lower={"divergence":"bullish"}
        flow={"state":"BUY"}
        score=app.score_direction(setup,"UP",flow,"LONG",lower)
        self.assertEqual(score,100)
        self.assertGreaterEqual(app.score_direction(setup,"UP",flow,"SHORT",lower),0)

if __name__=="__main__":unittest.main()
