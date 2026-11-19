import unittest
from badang_intratrade_stress import adverse_excursion

class IntratradeStressTests(unittest.TestCase):
    def setUp(self):
        self.rows=[(0,100,110,90,100,1),(1,100,105,80,95,1)]
    def test_long_adverse_extreme(self):
        r=adverse_excursion(self.rows,0,1,100,'LONG',leverage=2,margin=500)
        self.assertAlmostEqual(r['worst_intrabar_unrealized_pnl'],-200)
        self.assertFalse(r['actual_liquidation_verified'])
        self.assertIsNone(r['hypothetical_threshold_crossed'])
    def test_short_adverse_extreme(self):
        r=adverse_excursion(self.rows,0,1,100,'SHORT',leverage=2,margin=500)
        self.assertAlmostEqual(r['worst_intrabar_unrealized_pnl'],-100)
    def test_assumed_threshold_is_not_real_liquidation(self):
        r=adverse_excursion(self.rows,0,1,100,'LONG',leverage=5,margin=100,
                            assumed_maintenance_rate=.01)
        self.assertTrue(r['hypothetical_threshold_crossed'])
        self.assertFalse(r['actual_liquidation_verified'])
    def test_invalid_data(self):
        with self.assertRaises(ValueError):
            adverse_excursion(self.rows,1,0,100,'LONG')

if __name__=='__main__':unittest.main()
