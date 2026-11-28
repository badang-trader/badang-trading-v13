"""Regression: an empty successful cycle must fail closed."""
import json
import unittest
from badang_trade_runner_457 import safe_cycle_outcome, run_periodic

class EmptyCycleTests(unittest.TestCase):
    def test_empty_true_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Empty collection'):
            safe_cycle_outcome({'all_ok': True, 'results': []}, require_nonempty=True)

    def test_empty_false_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Empty collection'):
            safe_cycle_outcome({'all_ok': False, 'results': []}, require_nonempty=True)

    def test_empty_cycle_audited_as_failure(self):
        events, finishes = [], []
        run_periodic(run=lambda: {'all_ok': True, 'results': []}, interval=15,
                     max_cycles=1, emit=events.append, audit_start=lambda: 'run-1',
                     audit_finish=lambda rid, ok: finishes.append((rid, ok)), require_nonempty=True)
        self.assertEqual(finishes, [('run-1', False)])
        event = json.loads(events[0])
        self.assertFalse(event['all_ok'])
        self.assertTrue(event['audit_persisted'])
        self.assertFalse(event['coverage_confirmed'])

    def test_valid_cycle_still_passes(self):
        self.assertTrue(safe_cycle_outcome({'all_ok': True, 'results': [
            {'symbol': 'BTCUSDT', 'ok': True}]})['all_ok'])

if __name__ == '__main__': unittest.main()
