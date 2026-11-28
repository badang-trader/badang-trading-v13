"""Worker logs and audit must not trust inconsistent or secret-bearing results."""
import json
import unittest
from badang_trade_runner_457 import run_periodic


class RunnerSafetyTests(unittest.TestCase):
    def cycle(self, result):
        events = []
        def start():
            events.append('start')
            return 'test-run'
        def finish(run_id, ok):
            events.append(('finish', ok))
        run_periodic(run=lambda: result, interval=15, max_cycles=1,
                     emit=events.append, audit_start=start, audit_finish=finish)
        return events, json.loads(events[-1])

    def test_false_success_cannot_mark_audit_ok(self):
        events, log = self.cycle({'all_ok': True, 'results': [{'symbol': 'BTCUSDT', 'ok': False}]})
        self.assertEqual(events[1], ('finish', False))
        self.assertFalse(log['all_ok'])
        self.assertEqual(log['failure_phase'], 'collection')

    def test_unsupported_coverage_claim_fails_closed(self):
        events, log = self.cycle({'all_ok': True, 'results': [], 'coverage_confirmed': True})
        self.assertEqual(events[1], ('finish', False))
        self.assertFalse(log['all_ok'])

    def test_secret_fields_are_not_logged(self):
        events, log = self.cycle({'all_ok': True, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True, 'api_key': 'SECRET_TOKEN', 'sample_count': 2}]})
        self.assertEqual(events[1], ('finish', True))
        self.assertNotIn('SECRET_TOKEN', events[-1])
        self.assertEqual(log['results'], [{'symbol': 'BTCUSDT', 'ok': True}])

    def test_invalid_symbol_does_not_leak(self):
        events, log = self.cycle({'all_ok': True, 'results': [
            {'symbol': 'DATABASE_URL=secret', 'ok': True}]})
        self.assertFalse(log['all_ok'])
        self.assertNotIn('secret', events[-1])

    def test_valid_partial_failure_is_recorded(self):
        events, log = self.cycle({'all_ok': False, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True}, {'symbol': 'ETHUSDT', 'ok': False}]})
        self.assertEqual(events[1], ('finish', False))
        self.assertEqual(log['results'][1]['symbol'], 'ETHUSDT')

if __name__ == '__main__':
    unittest.main()
