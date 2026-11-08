"""Fail-closed verification of the database snapshot acknowledgement."""
import unittest
from badang_trade_job_455 import run_once

class StorageAcknowledgementTests(unittest.TestCase):
    def check_invalid(self, acknowledgement):
        result = run_once(['BTCUSDT'], lambda _: [],
                          lambda *args, **kwargs: acknowledgement, lambda: 1000)
        self.assertFalse(result['all_ok'])
        self.assertEqual(result['results'][0]['error_type'], 'ValueError')
        self.assertNotIn('sample_count', result['results'][0])
        self.assertFalse(result['coverage_confirmed'])

    def test_missing_sample(self): self.check_invalid({})
    def test_missing_count(self): self.check_invalid({'sample': {}})
    def test_boolean_count(self): self.check_invalid({'sample': {'sample_count': True}})
    def test_negative_count(self): self.check_invalid({'sample': {'sample_count': -1}})
    def test_oversized_count(self): self.check_invalid({'sample': {'sample_count': 101}})
    def test_string_count(self): self.check_invalid({'sample': {'sample_count': '2'}})
    def test_valid_zero_count(self):
        result = run_once(['BTCUSDT'], lambda _: [],
                          lambda *a, **kw: {'stored': True, 'coverage_confirmed': False, 'is_cvd': False, 'used_in_trading_score': False, 'sample': {'symbol': 'BTCUSDT', 'sample_count': 0}}, lambda: 1000)
        self.assertTrue(result['all_ok'])
        self.assertEqual(result['results'][0]['sample_count'], 0)
        self.assertFalse(result['coverage_confirmed'])

if __name__ == '__main__': unittest.main()
