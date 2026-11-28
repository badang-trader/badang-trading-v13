import unittest
from badang_live_readonly_gate_501 import inspect

OK = lambda: {'status':'DATABASE_PREFLIGHT_PASSED', 'mode':'read_only_database',
 'config_checks_passed':True,'db_check_attempted':True,'db_checks_passed':True,
 'live_exchange_verified':False,'continuous_cvd_verified':False,
 'trading_ready':False,'safe_to_enable_orders':False,'read_only':True,
                  'latest_run_snapshot_aligned':True,'worker_status':'RECENT_OK',
                  'snapshot_status':'ALL_TWO_RECENT_SAMPLES_ONLY'}
STORED = lambda: {'status':'SAMPLE_COUNTS_MATCH', 'coverage_confirmed':False,
                  'is_cvd':False, 'trading_ready':False,'read_only':True,
                  'checked_rows':4,'missing_symbols':[],
                  'bounded_to_latest_rows':True,'per_symbol_limit':200,
                  'inspected_symbols':['BTCUSDT','ETHUSDT'],
                  'rows_per_symbol':{'BTCUSDT':2,'ETHUSDT':2}}
WORKER = lambda: {'status':'RECENT_SAMPLES_AND_WORKER_ONLY', 'coverage_confirmed':False,
                  'continuous_cvd_verified':False,'trading_ready':False,'safe_to_enable_orders':False,'read_only':True,
                  'latest_run_snapshot_aligned':True,'worker_status':'RECENT_OK',
                  'snapshot_status':'ALL_TWO_RECENT_SAMPLES_ONLY'}

class LiveGateTests(unittest.TestCase):
    def test_happy_diagnostic_still_disables_orders(self):
        r=inspect(OK, STORED, WORKER)
        self.assertEqual(r['status'],'RECENT_REST_SAMPLES_ONLY')
        self.assertIs(r['safe_to_enable_orders'],False)
    def test_bad_preflight_skips_storage(self):
        def unexpected(): raise AssertionError('must not run')
        self.assertEqual(inspect(lambda:{'status':'CONFIGURATION_FAILED'},unexpected,unexpected)['status'],'PREFLIGHT_FAILED')
    def test_bad_storage_skips_worker(self):
        def unexpected(): raise AssertionError('must not run')
        self.assertEqual(inspect(OK,lambda:{'status':'COUNT_MISMATCH'},unexpected)['status'],'STORAGE_FAILED')
    def test_bad_worker_fails(self):
        self.assertEqual(inspect(OK,STORED,lambda:{'status':'WORKER_OR_SNAPSHOT_WARNING'})['status'],'WORKER_FAILED')
    def test_unverified_storage_claim_fails(self):
        self.assertEqual(inspect(OK,lambda:{**STORED(),'trading_ready':True},WORKER)['status'],'STORAGE_FAILED')
    def test_missing_storage_safety_flag_fails(self):
        self.assertEqual(inspect(OK,lambda:{'status':'SAMPLE_COUNTS_MATCH'},WORKER)['status'],'STORAGE_FAILED')
    def test_unverified_worker_claim_fails(self):
        self.assertEqual(inspect(OK,STORED,lambda:{**WORKER(),'safe_to_enable_orders':True})['status'],'WORKER_FAILED')
    def test_exception_message_not_exposed(self):
        def secret(): raise ValueError('postgres://user:secret@host/db')
        self.assertNotIn('secret',str(inspect(secret,STORED,WORKER)))

if __name__=='__main__': unittest.main()
