import unittest
from badang_readiness_476 import assess
from badang_db_preflight_473 import TABLES


class ReadinessTests(unittest.TestCase):
    def ok(self):
        return {'database_reachable': True, 'schema_ready': True,
                'tables_present': {name: True for name in TABLES}}

    def test_database_ready_never_means_trading_ready(self):
        result = assess(self.ok, lambda: {'schema_compatible': True})
        self.assertTrue(result['db_checks_passed'])
        self.assertFalse(result['trading_ready'])
        self.assertFalse(result['continuous_cvd_verified'])

    def test_schema_mismatch_fails_closed(self):
        self.assertFalse(assess(self.ok, lambda: {'schema_compatible': False})['db_checks_passed'])

    def test_missing_table_fails_closed(self):
        p = self.ok()
        p['tables_present'][TABLES[1]] = False
        self.assertFalse(assess(lambda: p, lambda: {'schema_compatible': True})['db_checks_passed'])

    def test_exception_does_not_leak_credentials(self):
        def bad():
            raise RuntimeError('postgres://user:secret@host/db')
        r = assess(bad, bad)
        self.assertNotIn('secret', str(r))
        self.assertTrue(r['preflight_error'])
        self.assertTrue(r['schema_error'])

    def test_malformed_response_fails_closed(self):
        self.assertFalse(assess(lambda: [], lambda: True)['db_checks_passed'])

    def test_false_values_are_not_truthy_success(self):
        p = self.ok()
        p['database_reachable'] = 1
        self.assertFalse(assess(lambda: p, lambda: {'schema_compatible': 1})['db_checks_passed'])


if __name__ == '__main__':
    unittest.main()
