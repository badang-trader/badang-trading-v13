import json
import subprocess
import sys
import unittest
from badang_render_verify_479 import report


class RenderVerificationTests(unittest.TestCase):
    def test_config_failure_does_not_contact_database(self):
        def never():
            raise AssertionError('database contacted')
        r = report(True, lambda: {'config_checks_passed': False}, never)
        self.assertEqual(r['status'], 'CONFIGURATION_FAILED')
        self.assertFalse(r['db_check_attempted'])

    def test_offline_pass_is_not_trading_ready(self):
        r = report(False, lambda: {'config_checks_passed': True})
        self.assertEqual(r['status'], 'CONFIGURATION_ONLY_PASSED')
        self.assertFalse(r['trading_ready'])
        self.assertFalse(r['safe_to_enable_orders'])

    def test_database_pass_is_not_exchange_verification(self):
        r = report(True, lambda: {'config_checks_passed': True},
                   lambda: {'db_check_attempted': True, 'db_checks_passed': True, 'predeploy_checks_passed': True})
        self.assertEqual(r['status'], 'DATABASE_PREFLIGHT_PASSED')
        self.assertFalse(r['continuous_cvd_verified'])
        self.assertFalse(r['safe_to_enable_orders'])

    def test_inconsistent_db_result_fails_closed(self):
        r = report(True, lambda: {'config_checks_passed': True},
                   lambda: {'db_check_attempted': False, 'db_checks_passed': True, 'predeploy_checks_passed': True})
        self.assertEqual(r['status'], 'DATABASE_FAILED')

    def test_errors_are_sanitized(self):
        def secret():
            raise RuntimeError('password=secret123')
        r = report(True, lambda: {'config_checks_passed': True}, secret)
        self.assertNotIn('secret123', json.dumps(r))
        self.assertEqual(r['status'], 'DATABASE_FAILED')

    def test_cli_offline_failure_returns_json_and_nonzero(self):
        import os
        env = dict(os.environ)
        env.pop('DATABASE_URL', None)
        p = subprocess.run([sys.executable, 'badang_render_verify_479.py'],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)['status'], 'CONFIGURATION_FAILED')


if __name__ == '__main__':
    unittest.main()
