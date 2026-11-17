import math
import unittest
from badang_position_scenarios import position_scenario

class PositionScenarioTests(unittest.TestCase):
    def test_long_weighted_entry_and_cost(self):
        r=position_scenario('LONG',2,100,1,90,110,0.1,0.1)
        self.assertAlmostEqual(r['average_entry'],290/3)
        self.assertAlmostEqual(r['gross_pnl_usdt'],40)
        self.assertAlmostEqual(r['assumed_cost_usdt'],(290+330)*.002)
        self.assertAlmostEqual(r['net_pnl_estimate_usdt'],38.76)
        self.assertIsNone(r['probability'])

    def test_short_profit_on_falling_price(self):
        r=position_scenario('SHORT',1,100,1,110,90)
        self.assertAlmostEqual(r['average_entry'],105)
        self.assertAlmostEqual(r['gross_pnl_usdt'],30)

    def test_no_added_quantity(self):
        r=position_scenario('LONG',2,100,0,0,105)
        self.assertEqual(r['average_entry'],100)
        self.assertEqual(r['gross_pnl_usdt'],10)

    def test_invalid_values(self):
        for args in [('LONG',1,100,-1,90,110),('LONG',1,100,1,90,float('nan')),
                     ('SHORT',0,100,0,90,110),('WAIT',1,100,1,90,110),
                     ('LONG',True,100,1,90,110)]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                position_scenario(*args)

if __name__=='__main__':
    unittest.main()
