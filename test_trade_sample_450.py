import unittest
from unittest.mock import patch
from badang_trade_sample_450 import parse_fills, snapshot

NOW = 1794000000000
class TradeSampleTests(unittest.TestCase):
    def test_sample_not_cvd(self):
        data = parse_fills([{'symbol':'BTCUSDT','side':'buy','size':'3','ts':NOW-1000,'tradeId':'1'},
                            {'symbol':'BTCUSDT','side':'sell','size':'1','ts':NOW-900,'tradeId':'2'}], 'BTCUSDT', NOW)
        self.assertEqual(data['sample_net_size'], 2)
        self.assertFalse(data['is_cvd'])
        self.assertFalse(data['coverage_confirmed'])
        self.assertFalse(data['used_in_trading_score'])
    def test_empty(self):
        self.assertEqual(parse_fills([], 'ETHUSDT', NOW)['status'], 'NO_SAMPLE')
    def test_mixed_symbol(self):
        with self.assertRaises(ValueError):
            parse_fills([{'symbol':'ETHUSDT','side':'buy','size':1,'ts':NOW}], 'BTCUSDT', NOW)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            parse_fills([{'side':'buy','size':1,'ts':NOW,'tradeId':'a'}]*2,'BTCUSDT',NOW)
    def test_bad_values(self):
        for side,size,ts in [('other',1,NOW),('buy',-1,NOW),('sell','nan',NOW),('buy',1,NOW+70000)]:
            with self.subTest(side=side,size=size,ts=ts), self.assertRaises(ValueError):
                parse_fills([{'side':side,'size':size,'ts':ts}],'BTCUSDT',NOW)
    def test_api_adapter(self):
        with patch('bitget_market_data._get', return_value=[] ) as getter:
            self.assertEqual(snapshot('BTCUSDT')['status'], 'NO_SAMPLE')
            self.assertEqual(getter.call_args.args[0], '/api/v2/mix/market/fills')

if __name__ == '__main__': unittest.main()
