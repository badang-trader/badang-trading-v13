"""No NaN/Inf or inverted structure may become an executable-looking plan."""
import math
import unittest
import app

BASE={"price":100.0,"atr":2.0,"swing_low":94.0,"swing_high":106.0}

class ScenarioFiniteTests(unittest.TestCase):
    def test_normal_long_and_short_have_correct_sides(self):
        for side in ("LONG","SHORT"):
            with self.subTest(side=side):
                p=app.scenario(BASE,side,"scalp")
                self.assertIsNotNone(p)
                self.assertTrue(all(math.isfinite(p[k]) for k in ("entry","stop","tp1","tp2")))
                if side=="LONG":
                    self.assertLess(p["stop"],p["entry"])
                    self.assertGreater(p["tp1"],p["entry"])
                else:
                    self.assertGreater(p["stop"],p["entry"])
                    self.assertLess(p["tp1"],p["entry"])
    def test_nonfinite_levels_fail_closed(self):
        for key in BASE:
            for value in (float("nan"),float("inf"),float("-inf")):
                with self.subTest(key=key,value=str(value)):
                    bad=dict(BASE,**{key:value})
                    self.assertIsNone(app.scenario(bad,"LONG","scalp"))
                    self.assertIsNone(app.scenario(bad,"SHORT","swing"))
    def test_inverted_or_nonpositive_structure_rejected(self):
        self.assertIsNone(app.scenario(dict(BASE,swing_low=108.0),"LONG","scalp"))
        self.assertIsNone(app.scenario(dict(BASE,swing_high=0.0),"SHORT","swing"))
    def test_unknown_direction_or_mode_rejected(self):
        self.assertIsNone(app.scenario(BASE,"WAIT","scalp"))
        self.assertIsNone(app.scenario(BASE,"LONG","unknown"))

if __name__=="__main__": unittest.main()
