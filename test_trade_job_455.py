import unittest
from badang_trade_job_455 import run_once, symbols_from_env


class TradeJobTests(unittest.TestCase):
    def test_symbols(self):
        self.assertEqual(symbols_from_env('btcusdt, ethusdt'), ['BTCUSDT','ETHUSDT'])
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): symbols_from_env('BTCUSDT,BTCUSDT')
    def test_empty_rejected(self):
        with self.assertRaises(ValueError): symbols_from_env('BTCUSDT,')
    def test_one_failure_does_not_stop_next_symbol(self):
        called=[]
        def fetch(symbol):
            called.append(symbol)
            if symbol=='BTCUSDT': raise TimeoutError('secret')
            return []
        def save(symbol,payload,fetched_ms):
            return {'stored': True, 'coverage_confirmed': False, 'is_cvd': False, 'used_in_trading_score': False, 'sample': {'symbol': symbol, 'sample_count':len(payload)}}
        result=run_once(['BTCUSDT','ETHUSDT'],fetch,save,lambda:1000)
        self.assertEqual(called,['BTCUSDT','ETHUSDT'])
        self.assertFalse(result['all_ok'])
        self.assertEqual(result['results'][0]['error_type'],'TimeoutError')
        self.assertNotIn('secret',str(result))
    def test_success_never_claims_cvd(self):
        result=run_once(['BTCUSDT'],lambda _:[],lambda *a,**kw:{'stored': True, 'coverage_confirmed': False, 'is_cvd': False, 'used_in_trading_score': False, 'sample': {'symbol': 'BTCUSDT', 'sample_count':0}},lambda:1000)
        self.assertTrue(result['all_ok'])
        self.assertFalse(result['is_cvd'])
        self.assertFalse(result['coverage_confirmed'])

if __name__=='__main__': unittest.main()
