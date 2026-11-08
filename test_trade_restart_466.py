"""Simulated process restart; this is NOT a live PostgreSQL integration test."""
import json
import unittest
from badang_trade_runner_457 import run_periodic
from badang_trade_runs_461 import assess_runs


class RestartSimulationTests(unittest.TestCase):
    def test_restart_after_unfinished_cycle_remains_unverified(self):
        rows = [(1000, None, 'running')]
        self.assertEqual(assess_runs(rows, 100000, 30000)['status'], 'INTERRUPTED_OR_RUNNING')
        calls = []
        output = []
        def start():
            calls.append('start')
            return 'new-run'
        def finish(rid, ok):
            calls.append(('finish', rid, ok))
        run_periodic(run=lambda: {'all_ok': True, 'results': []}, interval=15,
                     max_cycles=1, audit_start=start, audit_finish=finish, emit=output.append)
        self.assertEqual(calls, ['start', ('finish', 'new-run', True)])
        self.assertTrue(json.loads(output[0])['audit_persisted'])
        self.assertFalse(assess_runs(rows, 100000, 30000)['restart_verified'])

    def test_missing_finish_callback_fails_closed(self):
        with self.assertRaises(ValueError):
            run_periodic(run=lambda: self.fail('must not collect'), interval=15,
                         max_cycles=1, audit_start=lambda: 'id')

    def test_missing_start_callback_fails_closed(self):
        with self.assertRaises(ValueError):
            run_periodic(run=lambda: self.fail('must not collect'), interval=15,
                         max_cycles=1, audit_finish=lambda rid, ok: None)

    def test_invalid_audit_id_does_not_collect(self):
        for invalid in (None, '', '  ', 123):
            with self.subTest(invalid=invalid):
                output = []
                run_periodic(run=lambda: self.fail('must not collect'), interval=15,
                             max_cycles=1, audit_start=lambda: invalid,
                             audit_finish=lambda rid, ok: None, emit=output.append)
                event = json.loads(output[0])
                self.assertFalse(event['all_ok'])
                self.assertEqual(event['failure_phase'], 'audit_start')
                self.assertFalse(event['audit_persisted'])

    def test_collection_failure_marks_audit_failed(self):
        calls = []
        output = []
        def fail(): raise OSError('private credential')
        run_periodic(run=fail, interval=15, max_cycles=1,
                     audit_start=lambda: 'run-1',
                     audit_finish=lambda rid, ok: calls.append((rid, ok)), emit=output.append)
        self.assertEqual(calls, [('run-1', False)])
        self.assertNotIn('credential', output[0])

if __name__ == '__main__': unittest.main()
