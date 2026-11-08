"""Cost-model invariants for research-only backtesting."""
import unittest
from badang_cost_model_544 import net_round_trip as calc

class CostModelTests(unittest.TestCase):
    def test_flat_trade_loses_to_costs(self):
        for direction in ("long","short"):
            with self.subTest(direction=direction):
                self.assertLess(calc(100,100,direction)["net_return"],0)
    def test_favorable_move_not_always_profitable(self):
        self.assertLess(calc(100,100.1,"long")["net_return"],0)
        self.assertLess(calc(100,99.9,"short")["net_return"],0)
    def test_no_costs_match_directional_return(self):
        self.assertAlmostEqual(calc(100,110,"long",0,0)["net_return"],0.1)
        self.assertAlmostEqual(calc(100,90,"short",0,0)["net_return"],0.1)
    def test_higher_costs_never_improve_return(self):
        for direction,exit_price in (("long",105),("short",95)):
            a=calc(100,exit_price,direction,0.0002,0.0001)["net_return"]
            b=calc(100,exit_price,direction,0.001,0.001)["net_return"]
            self.assertLess(b,a)
    def test_invalid_inputs_fail_closed(self):
        for entry,exit_price,fee,slip in ((0,100,0,0),(100,float("nan"),0,0),
                                          (100,101,-0.1,0),(100,101,0,1)):
            with self.subTest(entry=entry,exit_price=exit_price,fee=fee,slip=slip):
                with self.assertRaises(ValueError):
                    calc(entry,exit_price,"long",fee,slip)
        with self.assertRaises(ValueError):
            calc(100,101,"buy")
if __name__=="__main__":unittest.main()
