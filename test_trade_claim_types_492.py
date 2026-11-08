import unittest
from badang_trade_runner_457 import safe_cycle_outcome


class ClaimTypeTests(unittest.TestCase):
    def base(self):
        return {'all_ok': True, 'results': [{'symbol': 'BTCUSDT', 'ok': True}]}

    def test_normal_false_claims_accepted(self):
        data = self.base()
        data['coverage_confirmed'] = False
        data['results'][0]['is_cvd'] = False
        self.assertTrue(safe_cycle_outcome(data, ['BTCUSDT'])['all_ok'])

    def test_top_level_non_boolean_claims_rejected(self):
        for bad in ('true', 'false', 1, 0, None, [], {}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                data = self.base()
                data['trading_ready'] = bad
                safe_cycle_outcome(data, ['BTCUSDT'])

    def test_symbol_non_boolean_claims_rejected(self):
        for bad in ('true', 'false', 1, 0, None, [], {}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                data = self.base()
                data['results'][0]['coverage_confirmed'] = bad
                safe_cycle_outcome(data, ['BTCUSDT'])

    def test_explicit_true_rejected(self):
        data = self.base()
        data['results'][0]['safe_to_enable_orders'] = True
        with self.assertRaises(ValueError):
            safe_cycle_outcome(data, ['BTCUSDT'])


if __name__ == '__main__':
    unittest.main()
