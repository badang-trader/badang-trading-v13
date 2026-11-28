import unittest
from badang_deploy_check_477 import assess_env

GOOD = {'DATABASE_URL':'postgresql://user:super-secret@db.example:5432/badang',
        'BADANG_TRADE_POLL_SECONDS':'60','BADANG_TRADE_SYMBOLS':'BTCUSDT,ETHUSDT'}

class DeployConfigTests(unittest.TestCase):
    def test_good_configuration_is_not_trading_readiness(self):
        r = assess_env(GOOD)
        self.assertTrue(r['config_checks_passed'])
        self.assertFalse(r['trading_ready'])
        self.assertFalse(r['db_connection_verified'])
    def test_missing_db_fails_closed(self):
        self.assertFalse(assess_env({})['config_checks_passed'])
    def test_bad_scheme_fails_closed(self):
        self.assertFalse(assess_env({**GOOD,'DATABASE_URL':'https://db.example/badang'})['config_checks_passed'])
    def test_bad_poll_fails_closed(self):
        self.assertFalse(assess_env({**GOOD,'BADANG_TRADE_POLL_SECONDS':'0'})['config_checks_passed'])
    def test_bad_symbols_fails_closed(self):
        self.assertFalse(assess_env({**GOOD,'BADANG_TRADE_SYMBOLS':'BTCUSDT,BTCUSDT'})['config_checks_passed'])
    def test_no_credentials_in_output(self):
        self.assertNotIn('super-secret',str(assess_env(GOOD)))
    def test_malformed_url_fails_closed(self):
        self.assertFalse(assess_env({**GOOD,'DATABASE_URL':'postgresql://[invalid/badang'})['config_checks_passed'])

if __name__ == '__main__': unittest.main()
