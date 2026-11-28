"""Do not count a database acknowledgement as success without a confirmed write."""
import unittest
from badang_trade_job_455 import run_once

class CommitAcknowledgementTests(unittest.TestCase):
    def setUp(self):
        self.good = {'stored': True, 'coverage_confirmed': False, 'is_cvd': False,
                     'used_in_trading_score': False,
                     'sample': {'symbol': 'BTCUSDT', 'sample_count': 1}}

    def check(self, ack, expected):
        out = run_once(['BTCUSDT'], lambda _: [], lambda *a, **kw: ack, lambda: 1000)
        self.assertEqual(out['all_ok'], expected)
        self.assertFalse(out['coverage_confirmed'])
        self.assertFalse(out['is_cvd'])

    def test_valid_ack(self): self.check(self.good, True)
    def test_missing_stored(self): self.check({k:v for k,v in self.good.items() if k!='stored'}, False)
    def test_false_stored(self): self.check(dict(self.good, stored=False), False)
    def test_string_stored(self): self.check(dict(self.good, stored='true'), False)
    def test_wrong_symbol(self): self.check(dict(self.good, sample={'symbol':'ETHUSDT','sample_count':1}), False)
    def test_missing_symbol(self): self.check(dict(self.good, sample={'sample_count':1}), False)
    def test_claimed_cvd(self): self.check(dict(self.good, is_cvd=True), False)
    def test_claimed_coverage(self): self.check(dict(self.good, coverage_confirmed=True), False)
    def test_claimed_trading_score(self): self.check(dict(self.good, used_in_trading_score=True), False)
    def test_string_false_claim(self): self.check(dict(self.good, is_cvd='false'), False)

if __name__ == '__main__': unittest.main()
