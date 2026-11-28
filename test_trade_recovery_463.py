import unittest
from badang_trade_recovery_463 import diagnose_restart

class RecoveryTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(diagnose_restart([], 1000, 100)['status'], 'NO_HISTORY')
    def test_previous_unfinished_with_later_success(self):
        result = diagnose_restart([(800, 850, 'ok'), (100, None, 'running')], 1000, 100)
        self.assertEqual(result['status'], 'PREVIOUS_UNFINISHED_RUN')
        self.assertTrue(result['later_run_observed'])
        self.assertFalse(result['backfill_verified'])
    def test_stale_latest(self):
        self.assertEqual(diagnose_restart([(100, None, 'running')], 1000, 100)['status'], 'LATEST_RUN_OVERDUE')
    def test_failure(self):
        self.assertEqual(diagnose_restart([(700, 750, 'failed')], 1000, 100)['status'], 'LATEST_FAILED')
    def test_good_history(self):
        self.assertEqual(diagnose_restart([(800, 900, 'ok'), (100, 200, 'ok')], 1000, 100)['status'], 'NO_INTERRUPTION_EVIDENCE')
    def test_invalid_chronology(self):
        with self.assertRaises(ValueError):
            diagnose_restart([(100, 200, 'ok'), (300, 400, 'ok')], 1000, 100)
    def test_invalid_running_finish(self):
        with self.assertRaises(ValueError):
            diagnose_restart([(100, 200, 'running')], 1000, 100)
    def test_no_cvd_promotion(self):
        result = diagnose_restart([(800, 900, 'ok')], 1000, 100)
        self.assertFalse(result['coverage_confirmed'])
        self.assertFalse(result['used_in_trading_score'])

if __name__ == '__main__': unittest.main()

class QueryRecoveryTests(unittest.TestCase):
    def test_bounded_query(self):
        from badang_trade_recovery_463 import latest_recovery
        class Cursor:
            def __init__(self): self.queries=[]
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def execute(self,*args): self.queries.append(args)
            def fetchall(self): return [(800,900,'ok'),(100,None,'running')]
        class Connection:
            def __init__(self): self.cur=Cursor()
            def cursor(self): return self.cur
            def close(self): pass
        c=Connection()
        result=latest_recovery(now_ms=1000, connect=lambda:c)
        self.assertEqual(result['previous_unfinished_runs'],1)
        self.assertIn('LIMIT %s',c.cur.queries[-1][0])
        self.assertEqual(c.cur.queries[-1][1],(25,))
        self.assertFalse(result['coverage_confirmed'])
