import unittest
from unittest.mock import patch
from badang_oi_parser_446 import parse_open_interest

class TestOIParser446(unittest.TestCase):
    def test_documented_list(self):
        self.assertEqual(parse_open_interest({'openInterestList':[{'symbol':'BTCUSDT','size':'1234.5'}]}),1234.5)
    def test_flat_list(self):
        self.assertEqual(parse_open_interest([{'size':'2.5'}]),2.5)
    def test_nested_single(self):
        self.assertEqual(parse_open_interest({'openInterest':'10'}),10)
    def test_bad_values(self):
        for v in [None,True,0,-1,'NaN','inf',{},[],[{},{}],{'openInterestList':[]}]:
            with self.subTest(v=v),self.assertRaises(ValueError): parse_open_interest(v)
    def test_postgres_observer_uses_parser(self):
        import badang_oi_postgres_443 as m
        with patch('bitget_market_data._get',return_value={'openInterestList':[{'size':'44'}]}),patch.object(m,'record') as record,patch.object(m,'changes',return_value={'status':'INSUFFICIENT_HISTORY'}):
            self.assertEqual(m.observe('BTCUSDT')['status'],'INSUFFICIENT_HISTORY')
            record.assert_called_once_with('BTCUSDT',44.0)

if __name__=='__main__': unittest.main()
