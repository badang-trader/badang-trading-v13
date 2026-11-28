import unittest
from badang_predeploy_478 import assess

class PredeployTests(unittest.TestCase):
    def test_pass_is_not_trading_ready(self):
        r=assess(lambda:{'config_checks_passed':True},lambda:{'db_checks_passed':True})
        self.assertTrue(r['predeploy_checks_passed'])
        self.assertFalse(r['trading_ready'])
        self.assertFalse(r['continuous_cvd_verified'])
    def test_bad_config_skips_db(self):
        def forbidden(): raise AssertionError('DB must not be called')
        r=assess(lambda:{'config_checks_passed':False},forbidden)
        self.assertFalse(r['db_check_attempted'])
        self.assertEqual(r['failure_stage'],'configuration')
    def test_config_exception_is_sanitized(self):
        def fail(): raise RuntimeError('secret password')
        r=assess(fail,lambda:None)
        self.assertNotIn('secret password',str(r))
        self.assertFalse(r['predeploy_checks_passed'])
    def test_bad_db_fails_closed(self):
        r=assess(lambda:{'config_checks_passed':True},lambda:{'db_checks_passed':False})
        self.assertTrue(r['db_check_attempted'])
        self.assertEqual(r['failure_stage'],'database')
    def test_db_exception_is_sanitized(self):
        def fail(): raise RuntimeError('postgres://secret')
        r=assess(lambda:{'config_checks_passed':True},fail)
        self.assertNotIn('secret',str(r))
    def test_non_dict_results_fail_closed(self):
        self.assertFalse(assess(lambda:True,lambda:{'db_checks_passed':True})['predeploy_checks_passed'])
        self.assertFalse(assess(lambda:{'config_checks_passed':True},lambda:True)['predeploy_checks_passed'])
    def test_truthy_values_do_not_pass(self):
        r=assess(lambda:{'config_checks_passed':1},lambda:{'db_checks_passed':True})
        self.assertFalse(r['predeploy_checks_passed'])
        r=assess(lambda:{'config_checks_passed':True},lambda:{'db_checks_passed':'true'})
        self.assertFalse(r['predeploy_checks_passed'])

if __name__=='__main__': unittest.main()
