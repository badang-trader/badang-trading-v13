import json
import unittest
from badang_trade_runner_457 import run_periodic


class RunnerAuditFailureTests(unittest.TestCase):
    def run_cycle(self, **kwargs):
        lines = []
        run_periodic(interval=15, max_cycles=1, emit=lines.append, **kwargs)
        return json.loads(lines[0])

    def test_successful_audit(self):
        calls = []
        result = self.run_cycle(run=lambda: {'all_ok': True, 'results': []},
            audit_start=lambda: 'id',
            audit_finish=lambda rid, ok: calls.append((rid, ok)))
        self.assertTrue(result['all_ok'])
        self.assertTrue(result['audit_persisted'])
        self.assertEqual(calls, [('id', True)])

    def test_finish_failure_is_not_success(self):
        calls = []
        def finish(rid, ok):
            calls.append((rid, ok))
            raise OSError('secret password')
        result = self.run_cycle(run=lambda: {'all_ok': True, 'results': []},
            audit_start=lambda: 'id', audit_finish=finish)
        self.assertFalse(result['all_ok'])
        self.assertEqual(result['failure_phase'], 'audit_finish')
        self.assertEqual(calls, [('id', True)])
        self.assertNotIn('password', json.dumps(result))

    def test_collection_failure_records_failed_audit(self):
        calls = []
        def fail(): raise RuntimeError('secret')
        result = self.run_cycle(run=fail, audit_start=lambda: 'id',
            audit_finish=lambda rid, ok: calls.append((rid, ok)))
        self.assertEqual(result['failure_phase'], 'collection')
        self.assertEqual(calls, [('id', False)])

    def test_start_failure_does_not_collect(self):
        def fail(): raise OSError('db down')
        result = self.run_cycle(run=lambda: self.fail('should not run'), audit_start=fail, audit_finish=lambda rid, ok: None)
        self.assertEqual(result['failure_phase'], 'audit_start')

    def test_invalid_outcome_is_failure(self):
        result = self.run_cycle(run=lambda: {'all_ok': 'yes', 'results': []})
        self.assertFalse(result['all_ok'])
        self.assertEqual(result['error_type'], 'ValueError')

    def test_no_audit_is_not_persisted(self):
        result = self.run_cycle(run=lambda: {'all_ok': True, 'results': []})
        self.assertFalse(result['audit_persisted'])

if __name__ == '__main__': unittest.main()
