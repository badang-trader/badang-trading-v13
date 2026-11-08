import unittest
from badang_live_readonly_gate_501 import inspect
from test_live_readonly_gate_501 import OK, STORED, WORKER

class SymbolEvidenceTests(unittest.TestCase):
    def check(self, **changes):
        return inspect(OK, lambda: {**STORED(), **changes}, WORKER)['status']
    def test_valid(self): self.assertEqual(self.check(), 'RECENT_REST_SAMPLES_ONLY')
    def test_missing_symbol(self): self.assertEqual(self.check(rows_per_symbol={'BTCUSDT':4}), 'STORAGE_FAILED')
    def test_zero_rows_for_eth(self): self.assertEqual(self.check(rows_per_symbol={'BTCUSDT':4,'ETHUSDT':0}), 'STORAGE_FAILED')
    def test_mismatched_total(self): self.assertEqual(self.check(checked_rows=5), 'STORAGE_FAILED')
    def test_duplicate_inspected(self): self.assertEqual(self.check(inspected_symbols=['BTCUSDT','BTCUSDT']), 'STORAGE_FAILED')
    def test_bool_count(self): self.assertEqual(self.check(rows_per_symbol={'BTCUSDT':True,'ETHUSDT':3}), 'STORAGE_FAILED')
    def test_over_limit(self): self.assertEqual(self.check(rows_per_symbol={'BTCUSDT':201,'ETHUSDT':2},checked_rows=203), 'STORAGE_FAILED')
    def test_missing_evidence(self): self.assertEqual(self.check(rows_per_symbol=None), 'STORAGE_FAILED')

if __name__ == '__main__': unittest.main()
