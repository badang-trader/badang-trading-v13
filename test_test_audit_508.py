import unittest
from unittest.mock import Mock
from badang_test_audit_508 import audit

class AuditTests(unittest.TestCase):
    def run_audit(self, errors=(), failures=(), skipped=(), count=4, successful=False):
        outcome=Mock()
        outcome.testsRun=count
        outcome.errors=list(errors)
        outcome.failures=list(failures)
        outcome.skipped=list(skipped)
        outcome.wasSuccessful.return_value=successful
        loader=Mock()
        loader.discover.return_value='suite'
        runner=Mock()
        runner.run.return_value=outcome
        return audit(loader=loader, runner=runner)
    def test_success(self):
        self.assertEqual(self.run_audit(successful=True)['status'],'ALL_TESTS_PASSED')
    def test_missing_flask(self):
        r=self.run_audit(errors=[('test',"ModuleNotFoundError: No module named 'flask'")])
        self.assertEqual(r['status'],'DEPENDENCY_BLOCKED')
        self.assertEqual(r['missing_dependencies'],['flask'])
    def test_no_traceback_leak(self):
        r=self.run_audit(errors=[('test',"password=private-token; No module named 'flask'")])
        self.assertNotIn('private-token',str(r))
    def test_failed(self):
        self.assertEqual(self.run_audit(failures=[('test','assert')])['status'],'TESTS_FAILED_OR_SKIPPED')
    def test_skipped_not_passed(self):
        self.assertEqual(self.run_audit(skipped=[('test','reason')],successful=True)['status'],'TESTS_FAILED_OR_SKIPPED')
    def test_zero_tests_not_passed(self):
        self.assertNotEqual(self.run_audit(count=0,successful=True)['status'],'ALL_TESTS_PASSED')
    def test_no_trading_claim(self):
        self.assertIs(self.run_audit(successful=True)['trading_ready'],False)
