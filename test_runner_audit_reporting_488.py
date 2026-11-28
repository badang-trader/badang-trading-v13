"""Regression tests: distinguish a persisted failed run from a failed audit write."""
import json
import unittest
from badang_trade_runner_457 import run_periodic

class AuditReportingTests(unittest.TestCase):
    def cycle(self, run, finish):
        logs=[]
        run_periodic(run=run, interval=15, max_cycles=1, emit=logs.append,
                     audit_start=lambda:'run-id', audit_finish=finish)
        return json.loads(logs[0])

    def test_collection_exception_with_persisted_failure(self):
        calls=[]
        def fail(): raise RuntimeError('secret')
        result=self.cycle(fail,lambda run_id, ok:calls.append((run_id,ok)))
        self.assertEqual(calls,[('run-id',False)])
        self.assertFalse(result['all_ok'])
        self.assertTrue(result['audit_persisted'])
        self.assertEqual(result['failure_phase'],'collection')
        self.assertNotIn('secret',str(result))

    def test_invalid_collection_with_persisted_failure(self):
        result=self.cycle(lambda:{'all_ok':True,'results':[{'symbol':'BTCUSDT','ok':False}]},
                          lambda run_id,ok:None)
        self.assertTrue(result['audit_persisted'])
        self.assertFalse(result['all_ok'])

    def test_collection_exception_with_failed_audit_write(self):
        def fail(): raise RuntimeError('secret')
        def fail_finish(run_id,ok): raise OSError('secret database')
        result=self.cycle(fail,fail_finish)
        self.assertFalse(result['audit_persisted'])
        self.assertFalse(result['all_ok'])
        self.assertNotIn('secret',str(result))

    def test_audit_finish_uncertain_not_retried(self):
        calls=[]
        def fail_finish(run_id,ok):
            calls.append(ok)
            raise OSError('commit uncertain')
        result=self.cycle(lambda:{'all_ok':True,'results':[]},fail_finish)
        self.assertEqual(calls,[True])
        self.assertEqual(result['failure_phase'],'audit_finish')
        self.assertFalse(result['audit_persisted'])

if __name__=='__main__': unittest.main()
