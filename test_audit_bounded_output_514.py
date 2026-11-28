"""Ensure noisy tests do not accumulate their output in memory."""
import io
import unittest
from unittest.mock import patch
import badang_test_audit_508 as mod

class FakeOutcome:
    testsRun = 1
    failures = []
    errors = []
    skipped = []
    def wasSuccessful(self): return True

class FakeLoader:
    def discover(self, *args, **kwargs):
        print('secret' * 100000)
        return object()

class FakeRunner:
    def run(self, suite):
        print('sensitive-output' * 100000)
        return FakeOutcome()

class BoundedOutputTests(unittest.TestCase):
    def test_sink_does_not_store_contents(self):
        sink = mod._BoundedSink()
        self.assertEqual(sink.write('password=very-secret'), len('password=very-secret'))
        self.assertEqual(sink.characters_discarded, 20)
        self.assertNotIn('secret', repr(sink.__dict__))

    def test_audit_large_output_is_suppressed(self):
        with patch.object(mod.io, 'StringIO', side_effect=AssertionError('unbounded capture')):
            result = mod.audit(loader=FakeLoader(), runner=FakeRunner())
        self.assertEqual(result['status'], 'ALL_TESTS_PASSED')
        self.assertFalse(result['trading_ready'])

    def test_sink_rejects_nontext(self):
        with self.assertRaises(TypeError): mod._BoundedSink().write(b'secret')

if __name__ == '__main__': unittest.main()
