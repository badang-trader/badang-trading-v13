"""End-to-end simulated worker lifecycle with an in-memory transactional DB.
No live PostgreSQL or Bitget is used.
"""
import unittest
import uuid
from badang_trade_runner_457 import run_periodic
from badang_trade_runs_461 import record_start, record_finish, assess_runs

class FakeDB:
    def __init__(self):
        self.rows = {}
        self.fail_finish = False
        self.commits = 0
        self.rollbacks = 0
    def connect(self):
        return FakeConnection(self)

class FakeConnection:
    def __init__(self, db):
        self.db = db
        self.pending = dict(db.rows)
    def __enter__(self): return self
    def __exit__(self, kind, *_):
        if kind:
            self.db.rollbacks += 1
        else:
            self.db.rows = self.pending
            self.db.commits += 1
    def close(self): pass
    def cursor(self): return FakeCursor(self)

class FakeCursor:
    def __init__(self, con): self.con = con; self.rowcount = -1
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def execute(self, sql, args=None):
        if sql.startswith('CREATE TABLE'): return
        if sql.startswith('INSERT INTO badang_trade_worker_runs'):
            run_id, start, state = args
            if run_id in self.con.pending: raise ValueError('duplicate run')
            self.con.pending[run_id] = (start, None, state)
        elif sql.startswith('UPDATE badang_trade_worker_runs'):
            if self.con.db.fail_finish: raise ConnectionError('simulated database failure')
            finished, state, run_id, expected, _ = args
            row = self.con.pending.get(run_id)
            self.rowcount = int(bool(row and row[2] == expected and row[0] <= finished))
            if self.rowcount: self.con.pending[run_id] = (row[0], finished, state)
        else: raise AssertionError(sql)

class LifecycleIntegrationTests(unittest.TestCase):
    def setUp(self): self.db = FakeDB(); self.events=[]
    def cycle(self, run):
        return run_periodic(run=run, interval=15, clock=lambda:0, max_cycles=1,
            emit=self.events.append,
            audit_start=lambda:record_start(started_ms=100,connect=self.db.connect),
            audit_finish=lambda rid, ok:record_finish(rid,ok,finished_ms=200,connect=self.db.connect))
    def test_success_commits_start_and_finish(self):
        self.cycle(lambda:{'all_ok':True,'results':[]})
        self.assertEqual([r[2] for r in self.db.rows.values()], ['ok'])
        self.assertIn('"audit_persisted": true', self.events[0])
        self.assertEqual(assess_runs(list(self.db.rows.values()),250,100)['status'],'RECENT_OK')
    def test_collector_failure_records_failed(self):
        def broken(): raise RuntimeError('offline')
        self.cycle(broken)
        self.assertEqual([r[2] for r in self.db.rows.values()], ['failed'])
        self.assertIn('"all_ok": false', self.events[0])
    def test_finish_database_failure_is_not_success(self):
        self.db.fail_finish=True
        self.cycle(lambda:{'all_ok':True,'results':[]})
        self.assertEqual([r[2] for r in self.db.rows.values()], ['running'])
        self.assertIn('"audit_persisted": false', self.events[0])
        self.assertIn('"failure_phase": "audit_finish"', self.events[0])
        self.assertEqual(self.db.rollbacks,1)
    def test_second_cycle_after_unfinished_run_does_not_claim_recovery(self):
        self.db.fail_finish=True
        self.cycle(lambda:{'all_ok':True,'results':[]})
        self.db.fail_finish=False
        self.cycle(lambda:{'all_ok':True,'results':[]})
        rows=sorted(self.db.rows.values(),key=lambda r:r[0],reverse=True)
        # Both runs share injected start time; use a distinct start time for the second run.
        self.assertEqual(len(rows),2)
        self.assertEqual(sum(r[2]=='running' for r in rows),1)
        self.assertFalse(assess_runs([(300,350,'ok'),(100,None,'running')],400,100)['restart_verified'])
    def test_duplicate_finish_rejected_without_mutation(self):
        rid=record_start(started_ms=100,connect=self.db.connect)
        record_finish(rid,True,finished_ms=200,connect=self.db.connect)
        with self.assertRaises(ValueError):
            record_finish(rid,False,finished_ms=300,connect=self.db.connect)
        self.assertEqual(self.db.rows[rid][2],'ok')

if __name__ == '__main__': unittest.main()
