"""Fail closed on contradictory safety claims in operational diagnostics."""
import unittest
from badang_live_readonly_gate_501 import inspect
from test_live_readonly_gate_501 import OK, STORED, WORKER

class SafetyClaimsTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual(inspect(OK, STORED, WORKER)['status'], 'RECENT_REST_SAMPLES_ONLY')
    def test_preflight_non_read_only(self):
        self.assertEqual(inspect(lambda: {**OK(), 'read_only': False}, STORED, WORKER)['status'], 'PREFLIGHT_FAILED')
    def test_preflight_false_coverage_claim(self):
        self.assertEqual(inspect(lambda: {**OK(), 'coverage_confirmed': True}, STORED, WORKER)['status'], 'PREFLIGHT_FAILED')
    def test_storage_orders_claim(self):
        self.assertEqual(inspect(OK, lambda: {**STORED(), 'safe_to_enable_orders': True}, WORKER)['status'], 'STORAGE_FAILED')
    def test_storage_cvd_claim(self):
        self.assertEqual(inspect(OK, lambda: {**STORED(), 'continuous_cvd_verified': 'false'}, WORKER)['status'], 'STORAGE_FAILED')
    def test_worker_cvd_claim(self):
        self.assertEqual(inspect(OK, STORED, lambda: {**WORKER(), 'is_cvd': True})['status'], 'WORKER_FAILED')
    def test_worker_score_claim(self):
        self.assertEqual(inspect(OK, STORED, lambda: {**WORKER(), 'used_in_trading_score': 1})['status'], 'WORKER_FAILED')

if __name__ == '__main__': unittest.main()
