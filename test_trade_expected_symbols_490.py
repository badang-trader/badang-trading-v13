import json
import unittest
from badang_trade_runner_457 import safe_cycle_outcome, run_periodic

class ExpectedSymbolsTests(unittest.TestCase):
    def test_exact_set_passes(self):
        result = safe_cycle_outcome({'all_ok': True, 'results': [{'symbol':'ETHUSDT','ok':True},{'symbol':'BTCUSDT','ok':True}]}, ['BTCUSDT','ETHUSDT'])
        self.assertTrue(result['all_ok'])
    def test_missing_symbol_fails(self):
        with self.assertRaisesRegex(ValueError, 'symbol set mismatch'):
            safe_cycle_outcome({'all_ok':True,'results':[{'symbol':'BTCUSDT','ok':True}]}, ['BTCUSDT','ETHUSDT'])
    def test_extra_symbol_fails(self):
        with self.assertRaisesRegex(ValueError, 'symbol set mismatch'):
            safe_cycle_outcome({'all_ok':True,'results':[{'symbol':'BTCUSDT','ok':True},{'symbol':'ETHUSDT','ok':True}]}, ['BTCUSDT'])
    def test_missing_symbol_audit_failed(self):
        logs=[]; finishes=[]
        run_periodic(run=lambda:{'all_ok':True,'results':[{'symbol':'BTCUSDT','ok':True}]},
                     expected_symbols=['BTCUSDT','ETHUSDT'],max_cycles=1,interval=15,
                     emit=logs.append,audit_start=lambda:'run1',
                     audit_finish=lambda rid,ok:finishes.append((rid,ok)))
        self.assertEqual(finishes,[('run1',False)])
        self.assertFalse(json.loads(logs[0])['all_ok'])
        self.assertTrue(json.loads(logs[0])['audit_persisted'])
    def test_empty_result_fails(self):
        with self.assertRaisesRegex(ValueError,'symbol set mismatch'):
            safe_cycle_outcome({'all_ok':True,'results':[]},['BTCUSDT'])

if __name__=='__main__': unittest.main()
