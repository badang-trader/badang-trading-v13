"""Fail-closed research cost inputs and malformed historical fills."""
import unittest
from badang_research_cost_sensitivity_560 import cost_sensitivity
from badang_research_backtest_545 import evaluate_signal

class ResearchCostInputTests(unittest.TestCase):
    def setUp(self):
        self.trade={"raw_entry":100,"raw_exit":101,"direction":"long"}
    def test_negative_and_nonfinite_costs_rejected(self):
        for costs in ((-0.01,0),(0,-0.01),(float("nan"),0),(0,float("inf")),(1,0),(0,1)):
            with self.subTest(costs=costs),self.assertRaises(ValueError):
                cost_sensitivity([self.trade],{"invalid":costs})
    def test_missing_raw_fills_rejected(self):
        for key in ("raw_entry","raw_exit","direction"):
            trade=dict(self.trade)
            del trade[key]
            with self.subTest(key=key),self.assertRaises((ValueError,KeyError)):
                cost_sensitivity([trade])
    def test_zero_or_negative_fill_rejected(self):
        for key in ("raw_entry","raw_exit"):
            trade=dict(self.trade)
            trade[key]=0
            with self.subTest(key=key),self.assertRaises(ValueError):
                cost_sensitivity([trade])
    def test_historical_bar_nonfinite_price_rejected(self):
        bars=[{"open":100,"close":100} for _ in range(12)]
        bars[3]["open"]=float("nan")
        with self.assertRaises(ValueError):
            evaluate_signal(bars,2,"long",3)
    def test_invalid_scenario_schema_rejected(self):
        for scenarios in ({}, {"":(.001,.001)}, {"bad":(.001,)}, {"bad":"oops"}):
            with self.subTest(scenarios=scenarios),self.assertRaises(ValueError):
                cost_sensitivity([self.trade],scenarios)
if __name__=="__main__":unittest.main()
