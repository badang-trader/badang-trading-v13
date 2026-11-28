"""Audit output must never echo incidental stdout/stderr from test modules."""
import contextlib
import io
import unittest
from unittest.mock import patch
import badang_test_audit_508 as mod

class FakeOutcome:
    testsRun=1
    failures=[]
    errors=[]
    skipped=[]
    def wasSuccessful(self): return True

class NoisyLoader:
    def discover(self, *args, **kwargs):
        print('FAKE_SECRET_FROM_IMPORT')
        return object()

class NoisyRunner:
    def run(self, suite):
        print('FAKE_SECRET_FROM_TEST')
        import sys
        print('FAKE_SECRET_STDERR', file=sys.stderr)
        return FakeOutcome()

class AuditOutputTests(unittest.TestCase):
    def test_capture_discovery_and_test_output(self):
        out, err=io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result=mod.audit(loader=NoisyLoader(),runner=NoisyRunner())
        self.assertEqual(result['status'],'ALL_TESTS_PASSED')
        self.assertEqual(out.getvalue(),'')
        self.assertEqual(err.getvalue(),'')
    def test_cli_prints_only_sanitized_json(self):
        out=io.StringIO()
        with patch.object(mod,'audit',return_value={'status':'ALL_TESTS_PASSED'}):
            with contextlib.redirect_stdout(out):
                self.assertEqual(mod.main([]),0)
        self.assertNotIn('SECRET',out.getvalue())

if __name__=='__main__': unittest.main()
