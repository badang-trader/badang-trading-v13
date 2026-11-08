"""Audit must never hide unrelated test failures behind missing dependencies."""
import unittest
from unittest.mock import Mock
from badang_test_audit_508 import audit

class MixedOutcomeTests(unittest.TestCase):
    def check(self, errors=(), failures=(), skipped=()):
        outcome=Mock(testsRun=5, errors=list(errors), failures=list(failures), skipped=list(skipped))
        outcome.wasSuccessful.return_value=False
        loader=Mock(); loader.discover.return_value='suite'
        runner=Mock(); runner.run.return_value=outcome
        return audit(loader=loader, runner=runner)
    def test_only_dependency_error(self):
        self.assertEqual(self.check(errors=[('a',"No module named 'flask'")])['status'],'DEPENDENCY_BLOCKED')
    def test_dependency_plus_failure(self):
        r=self.check(errors=[('a',"No module named 'flask'")],failures=[('b','assert')])
        self.assertEqual(r['status'],'TESTS_FAILED_OR_SKIPPED')
        self.assertEqual(r['missing_dependencies'],['flask'])
    def test_dependency_plus_other_error(self):
        self.assertEqual(self.check(errors=[('a',"No module named 'flask'"),('b','RuntimeError: broken')])['status'],'TESTS_FAILED_OR_SKIPPED')
    def test_dependency_plus_skip(self):
        self.assertEqual(self.check(errors=[('a',"No module named 'flask'")],skipped=[('b','skip')])['status'],'TESTS_FAILED_OR_SKIPPED')
    def test_no_secret_in_result(self):
        self.assertNotIn('secret-token',str(self.check(errors=[('a',"secret-token No module named 'flask'")])))

if __name__=='__main__': unittest.main()
