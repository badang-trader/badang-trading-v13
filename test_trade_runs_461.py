import unittest
from badang_trade_runs_461 import assess_runs
from badang_trade_runner_457 import run_periodic

class RunAuditTests(unittest.TestCase):
    def test_no_runs(self):
        self.assertEqual(assess_runs([], 1000, 100)['status'], 'NO_RUNS')
    def test_stale_running(self):
        self.assertEqual(assess_runs([(100, None, 'running')], 500, 100)['status'], 'INTERRUPTED_OR_RUNNING')
    def test_recent_ok(self):
        self.assertEqual(assess_runs([(100, 150, 'ok')], 200, 100)['status'], 'RECENT_OK')
    def test_failed(self):
        self.assertEqual(assess_runs([(100, 150, 'failed')], 200, 100)['status'], 'FAILED')
    def test_future(self):
        self.assertEqual(assess_runs([(500, None, 'running')], 200, 100)['status'], 'CLOCK_ANOMALY')
    def test_runner_records_success(self):
        events=[]
        run_periodic(run=lambda: {'all_ok':True,'results':[]}, interval=15,
                     clock=lambda: 0, max_cycles=1, emit=lambda s:None,
                     audit_start=lambda:'id', audit_finish=lambda i,ok:events.append((i,ok)))
        self.assertEqual(events,[('id',True)])
    def test_runner_records_failure(self):
        events=[]
        def fail(): raise ValueError('bad')
        run_periodic(run=fail, interval=15, clock=lambda:0, max_cycles=1,
                     emit=lambda s:None, audit_start=lambda:'id',
                     audit_finish=lambda i,ok:events.append((i,ok)))
        self.assertEqual(events,[('id',False)])

if __name__=='__main__': unittest.main()
