import unittest
from unittest.mock import patch
import badang_oi_job_444 as job

class TestOIJob(unittest.TestCase):
    def test_parse_dedup(self):
        self.assertEqual(job.parse_symbols('btcusdt,ETHUSDT,btcusdt'), ['BTCUSDT', 'ETHUSDT'])
    def test_reject_invalid(self):
        for raw in ('', 'BTCUSDT,,ETHUSDT', ','.join(['BTCUSDT']*21), 'BTC/USDT'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                job.parse_symbols(raw)
    def test_success(self):
        result = job.collect_once(['BTCUSDT'], lambda s: {'status': 'PARTIAL_HISTORY'}, 0)
        self.assertEqual(result, [{'symbol':'BTCUSDT','ok':True,'status':'PARTIAL_HISTORY'}])
    def test_failure_isolated_and_redacted(self):
        def observer(symbol):
            if symbol == 'BTCUSDT':
                raise RuntimeError('postgres://secret:password@server')
            return {'status':'INSUFFICIENT_HISTORY'}
        result = job.collect_once(['BTCUSDT', 'ETHUSDT'], observer, 0)
        self.assertEqual(len(result), 2)
        self.assertFalse(result[0]['ok'])
        self.assertNotIn('password', str(result))
        self.assertTrue(result[1]['ok'])
    def test_requires_database(self):
        with patch.dict('os.environ', {'DATABASE_URL':''}):
            self.assertEqual(job.main(['--symbols','BTCUSDT']), 2)

if __name__ == '__main__': unittest.main()
