"""Only the terminal exception may classify a test as dependency blocked."""
import unittest
from unittest.mock import Mock
from badang_test_audit_508 import audit

class FinalExceptionTests(unittest.TestCase):
    def check(self, trace):
        outcome=Mock(testsRun=1, errors=[('case',trace)], failures=[], skipped=[])
        outcome.wasSuccessful.return_value=False
        loader=Mock(); loader.discover.return_value='suite'
        runner=Mock(); runner.run.return_value=outcome
        return audit(loader=loader, runner=runner)
    def test_actual_missing_flask(self):
        self.assertEqual(self.check('Traceback...\nModuleNotFoundError: No module named \'flask\'')['status'],'DEPENDENCY_BLOCKED')
    def test_earlier_flask_mention_not_dependency(self):
        r=self.check('ModuleNotFoundError: No module named \'flask\'\nRuntimeError: other failure')
        self.assertEqual(r['status'],'TESTS_FAILED_OR_SKIPPED')
        self.assertEqual(r['missing_dependencies'],[])
    def test_importerror(self):
        self.assertEqual(self.check('ImportError: No module named \'requests\'')['status'],'DEPENDENCY_BLOCKED')
    def test_submodule(self):
        self.assertEqual(self.check('ModuleNotFoundError: No module named \'flask.testing\'')['missing_dependencies'],['flask'])
    def test_unknown_dependency(self):
        self.assertEqual(self.check('ModuleNotFoundError: No module named \'internal_badang\'')['status'],'TESTS_FAILED_OR_SKIPPED')
    def test_quoted_message_not_dependency(self):
        self.assertEqual(self.check('RuntimeError: No module named \'flask\'')['status'],'TESTS_FAILED_OR_SKIPPED')
    def test_no_sensitive_trace(self):
        self.assertNotIn('private-password',str(self.check('private-password\nRuntimeError: failed')))

if __name__=='__main__': unittest.main()
