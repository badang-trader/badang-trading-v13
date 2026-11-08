import unittest
from badang_live_readonly_gate_501 import inspect
from test_live_readonly_gate_501 import OK, STORED, WORKER

class EvidenceTests(unittest.TestCase):
    def test_happy(self):
        self.assertEqual(inspect(OK, STORED, WORKER)['status'], 'RECENT_REST_SAMPLES_ONLY')
    def test_no_rows(self):
        self.assertEqual(inspect(OK, lambda:{**STORED(), 'checked_rows':0}, WORKER)['status'], 'STORAGE_FAILED')
    def test_bool_rows(self):
        self.assertEqual(inspect(OK, lambda:{**STORED(), 'checked_rows':True}, WORKER)['status'], 'STORAGE_FAILED')
    def test_missing_symbol(self):
        self.assertEqual(inspect(OK, lambda:{**STORED(), 'missing_symbols':['ETHUSDT']}, WORKER)['status'], 'STORAGE_FAILED')
    def test_unbounded(self):
        self.assertEqual(inspect(OK, lambda:{**STORED(), 'bounded_to_latest_rows':False}, WORKER)['status'], 'STORAGE_FAILED')
    def test_unaligned(self):
        self.assertEqual(inspect(OK, STORED, lambda:{**WORKER(), 'latest_run_snapshot_aligned':False})['status'], 'WORKER_FAILED')
    def test_missing_worker_provenance(self):
        self.assertEqual(inspect(OK, STORED, lambda:{k:v for k,v in WORKER().items() if k!='worker_status'})['status'], 'WORKER_FAILED')
    def test_worker_wrong_snapshot_status(self):
        self.assertEqual(inspect(OK, STORED, lambda:{**WORKER(), 'snapshot_status':'UNKNOWN'})['status'], 'WORKER_FAILED')

if __name__ == '__main__': unittest.main()
