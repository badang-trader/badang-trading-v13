import unittest
from badang_live_readonly_gate_501 import inspect
from test_live_readonly_gate_501 import OK, STORED, WORKER

class GateTrustTests(unittest.TestCase):
    def test_missing_db_evidence(self):
        for key in ('mode','config_checks_passed','db_check_attempted','db_checks_passed'):
            with self.subTest(key=key):
                self.assertEqual(inspect(lambda:{k:v for k,v in OK().items() if k!=key},STORED,WORKER)['status'],'PREFLIGHT_FAILED')
    def test_fake_preflight_claim(self):
        for key in ('live_exchange_verified','continuous_cvd_verified','trading_ready','safe_to_enable_orders'):
            with self.subTest(key=key):
                self.assertEqual(inspect(lambda:{**OK(),key:True},STORED,WORKER)['status'],'PREFLIGHT_FAILED')
    def test_offline_mode_rejected(self):
        self.assertEqual(inspect(lambda:{**OK(),'mode':'offline_configuration'},STORED,WORKER)['status'],'PREFLIGHT_FAILED')
    def test_missing_read_only_storage(self):
        self.assertEqual(inspect(OK,lambda:{k:v for k,v in STORED().items() if k!='read_only'},WORKER)['status'],'STORAGE_FAILED')
    def test_missing_read_only_worker(self):
        self.assertEqual(inspect(OK,STORED,lambda:{k:v for k,v in WORKER().items() if k!='read_only'})['status'],'WORKER_FAILED')
    def test_normal_diagnostic(self):
        self.assertEqual(inspect(OK,STORED,WORKER)['status'],'RECENT_REST_SAMPLES_ONLY')

if __name__=='__main__': unittest.main()
