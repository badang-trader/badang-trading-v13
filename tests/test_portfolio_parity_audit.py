import copy
import unittest
from badang_portfolio_parity_audit import verify

class ParityAuditTests(unittest.TestCase):
    def setUp(self):
        self.a={'results':[{'strategy':'early','partition':'HOLDOUT','filter':'NONE',
                            'accepted':2,'rejected_insufficient_margin':1,
                            'ending_capital':10010.,'realized_return':.001,
                            'realized_event_drawdown':.03}]}
        self.b={'results':[{'strategy':'early','partition':'HOLDOUT','filter':'NONE',
                            'accepted':2,'rejected_insufficient_margin':1,
                            'ending_realized_cash':10010.,'realized_return':.001,
                            'realized_event_drawdown':.03}]}
    def test_pass(self):
        self.assertEqual(verify(self.a,self.b)['status'],'PASS')
    def test_detect_mismatch(self):
        b=copy.deepcopy(self.b);b['results'][0]['ending_realized_cash']+=1
        with self.assertRaisesRegex(ValueError,'parity mismatch'):verify(self.a,b)
    def test_detect_missing_scenario(self):
        with self.assertRaisesRegex(ValueError,'scenario count'):verify(self.a,{'results':[]})
    def test_detect_duplicate_scenario(self):
        with self.assertRaisesRegex(ValueError,'duplicate synchronized'):
            verify({'results':self.a['results']*2},{'results':self.b['results']*2})

if __name__=='__main__':unittest.main()
