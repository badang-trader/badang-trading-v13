"""Ensure audit output symbol identifiers are ASCII-only."""
import json
import unittest
from badang_trade_runner_457 import safe_cycle_outcome, run_periodic

class SymbolAsciiTests(unittest.TestCase):
    def test_unicode_lookalike_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid symbol'):
            safe_cycle_outcome({'all_ok': True, 'results': [{'symbol': 'ＢＴＣＵＳＤＴ', 'ok': True}]})

    def test_unicode_digits_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid symbol'):
            safe_cycle_outcome({'all_ok': True, 'results': [{'symbol': 'BTC١', 'ok': True}]})

    def test_ascii_symbol_preserved(self):
        self.assertTrue(safe_cycle_outcome({'all_ok': True, 'results': [{'symbol': 'BTCUSDT', 'ok': True}]})['all_ok'])

    def test_bad_symbol_marks_cycle_failed(self):
        logs, finishes = [], []
        run_periodic(run=lambda: {'all_ok': True, 'results': [{'symbol': 'BTC١', 'ok': True}]},
                     max_cycles=1, interval=15, emit=logs.append, audit_start=lambda: 'id',
                     audit_finish=lambda rid, ok: finishes.append((rid, ok)))
        self.assertEqual(finishes, [('id', False)])
        self.assertFalse(json.loads(logs[0])['all_ok'])

if __name__ == '__main__': unittest.main()
