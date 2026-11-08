import unittest
from badang_trade_job_456 import fetch_with_retry, run_once_with_retry

class RetryTests(unittest.TestCase):
    def test_transient_fetch_retries_and_backoff(self):
        calls=[]; waits=[]
        def fetch(symbol):
            calls.append(symbol)
            if len(calls)<3: raise TimeoutError('temporary')
            return [1]
        self.assertEqual(fetch_with_retry('BTCUSDT',fetch,waits.append,3,0.5),[1])
        self.assertEqual(len(calls),3)
        self.assertEqual(waits,[0.5,1.0])
    def test_permanent_failure_no_retry(self):
        calls=[]
        def fetch(s): calls.append(s); raise ValueError('invalid payload')
        with self.assertRaises(ValueError): fetch_with_retry('BTCUSDT',fetch,lambda _:None)
        self.assertEqual(len(calls),1)
    def test_exhaustion(self):
        waits=[]
        with self.assertRaises(ConnectionError):
            fetch_with_retry('BTCUSDT',lambda _:(_ for _ in ()).throw(ConnectionError()),waits.append,3,1)
        self.assertEqual(waits,[1,2])
    def test_write_not_retried(self):
        calls=[]
        def save(*args,**kwargs): calls.append(1); raise TimeoutError('ambiguous commit')
        result=run_once_with_retry(['BTCUSDT'],lambda _:[],save,lambda:1000,lambda _:None)
        self.assertFalse(result['all_ok'])
        self.assertEqual(len(calls),1)
        self.assertFalse(result['is_cvd'])
    def test_invalid_config(self):
        for attempts in (0,6,1.2):
            with self.assertRaises(ValueError): fetch_with_retry('BTCUSDT',lambda _:[],attempts=attempts)
    def test_one_symbol_exhausted_other_continues(self):
        calls=[]
        def fetch(s):
            calls.append(s)
            if s=='BTCUSDT': raise TimeoutError()
            return []
        result=run_once_with_retry(['BTCUSDT','ETHUSDT'],fetch,
            lambda symbol,*a,**kw:{'stored': True, 'coverage_confirmed': False, 'is_cvd': False, 'used_in_trading_score': False, 'sample': {'symbol': symbol, 'sample_count':0}},lambda:1000,lambda _:None,2,0)
        self.assertEqual(calls,['BTCUSDT','BTCUSDT','ETHUSDT'])
        self.assertFalse(result['all_ok'])
        self.assertTrue(result['results'][1]['ok'])

if __name__=='__main__': unittest.main()
