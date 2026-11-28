"""Offline acceptance tests of the actual worker entry point (no live services)."""
import json
import unittest
from badang_trade_runner_457 import run_periodic


class WorkerAcceptance493(unittest.TestCase):
    def exercise(self, outcome=None, failure=None, finish_failure=False):
        events, audits = [], []
        def start():
            audits.append(('start', 'run-1'))
            return 'run-1'
        def finish(run_id, success):
            audits.append(('finish', run_id, success))
            if finish_failure:
                raise RuntimeError('database password must not leak')
        def run():
            if failure:
                raise RuntimeError('API SECRET must not leak')
            return outcome
        count = run_periodic(run=run, interval=15, max_cycles=1,
            expected_symbols=['BTCUSDT', 'ETHUSDT'],
            audit_start=start, audit_finish=finish,
            emit=lambda line: events.append(json.loads(line)),
            clock=lambda: 0)
        self.assertEqual(count, 1)
        self.assertEqual(len(events), 1)
        self.assertNotIn('SECRET', json.dumps(events))
        self.assertNotIn('password', json.dumps(events))
        return events[0], audits

    def test_two_symbols_success(self):
        event, audits = self.exercise({'all_ok': True, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True}, {'symbol': 'ETHUSDT', 'ok': True}]})
        self.assertTrue(event['all_ok'])
        self.assertTrue(event['audit_persisted'])
        self.assertEqual(audits[-1], ('finish', 'run-1', True))
        self.assertFalse(event['coverage_confirmed'])
        self.assertFalse(event['is_cvd'])

    def test_missing_symbol_fails_closed(self):
        event, audits = self.exercise({'all_ok': True, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True}]})
        self.assertFalse(event['all_ok'])
        self.assertTrue(event['audit_persisted'])
        self.assertEqual(audits[-1], ('finish', 'run-1', False))

    def test_collection_exception_audited_as_failure(self):
        event, audits = self.exercise(failure=True)
        self.assertFalse(event['all_ok'])
        self.assertEqual(event['failure_phase'], 'collection')
        self.assertEqual(audits[-1], ('finish', 'run-1', False))

    def test_failed_finish_never_reports_persisted(self):
        event, audits = self.exercise({'all_ok': True, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True}, {'symbol': 'ETHUSDT', 'ok': True}]}, finish_failure=True)
        self.assertFalse(event['all_ok'])
        self.assertFalse(event['audit_persisted'])
        self.assertEqual(event['failure_phase'], 'audit_finish')
        self.assertEqual(len([a for a in audits if a[0]=='finish']), 1)

    def test_forged_cvd_claim_fails_closed(self):
        event, audits = self.exercise({'all_ok': True, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True, 'is_cvd': True},
            {'symbol': 'ETHUSDT', 'ok': True}]})
        self.assertFalse(event['all_ok'])
        self.assertEqual(audits[-1], ('finish', 'run-1', False))

if __name__ == '__main__':
    unittest.main()
