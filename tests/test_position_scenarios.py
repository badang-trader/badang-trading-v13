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

    def test_read_only_flask_endpoint(self):
        from app import app
        client=app.test_client()
        payload={'side':'LONG','existing_quantity':2,'existing_entry':100,
                 'added_quantity':1,'added_entry':90,'exit_price':110,
                 'fee_pct':0.1,'slippage_pct':0.1}
        response=client.post('/api/position-scenario',json=payload)
        self.assertEqual(response.status_code,200)
        self.assertAlmostEqual(response.get_json()['average_entry'],290/3)
        self.assertIsNone(response.get_json()['probability'])
        self.assertEqual(client.post('/api/position-scenario',
                         json={**payload,'added_quantity':-1}).status_code,400)
        self.assertEqual(client.get('/api/position-scenario').status_code,405)

    def test_invalid_values(self):
        for args in [('LONG',1,100,-1,90,110),('LONG',1,100,1,90,float('nan')),
                     ('SHORT',0,100,0,90,110),('WAIT',1,100,1,90,110),
                     ('LONG',True,100,1,90,110)]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                position_scenario(*args)

if __name__=='__main__':
    unittest.main()
