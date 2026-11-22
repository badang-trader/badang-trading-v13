import unittest
from badang_censored_equity_replay import replay

class CensoredEquityReplayTests(unittest.TestCase):
    def test_margin_reserved_and_no_fabricated_exit(self):
        e=[dict(id="a",symbol="BTC",timeframe="15m",side="LONG",entry_ts=0,entry_price=100,leverage=2,reason="END_OF_DATA"),
           dict(id="b",symbol="ETH",timeframe="15m",side="SHORT",entry_ts=0,entry_price=100,leverage=2,reason="END_OF_DATA")]
        h={("BTC","15m"):[[0,100,110,90,105,1]],("ETH","15m"):[[0,100,110,90,95,1]]}
        r=replay(e,h,[900000],initial_capital=1000,margin_fraction=.2,max_margin_fraction=.3)
        self.assertEqual(len(r["rejected"]),1)
        self.assertEqual(r["snapshots"][0]["reserved_margin"],200)
        self.assertEqual(r["snapshots"][0]["realized_pnl"],0)
        self.assertEqual(r["snapshots"][0]["strict_observed_equity"],1020)
        self.assertEqual(len(r["unclosed_ids"]),1)
    def test_stale_is_not_strict_equity(self):
        e=[dict(id="a",symbol="BTC",timeframe="15m",side="LONG",entry_ts=0,entry_price=100,leverage=2,reason="END_OF_DATA")]
        h={("BTC","15m"):[[0,100,110,90,105,1]]}
        r=replay(e,h,[1800000],initial_capital=1000)
        self.assertIsNone(r["snapshots"][0]["strict_observed_equity"])
        self.assertEqual(r["snapshots"][0]["non_exact_marks"][0]["age_ms"],900000)
    def test_same_time_exit_cannot_fund_entry(self):
        a=dict(id="a",symbol="BTC",timeframe="15m",side="LONG",entry_ts=0,exit_ts=900000,entry_price=100,leverage=2,net_return=0,reason="CLOSED")
        b=dict(id="b",symbol="BTC",timeframe="15m",side="LONG",entry_ts=900000,entry_price=100,leverage=2,reason="END_OF_DATA")
        h={("BTC","15m"):[[0,100,110,90,100,1]]}
        r=replay([a,b],h,[900000],initial_capital=1000,margin_fraction=.2,max_margin_fraction=.3)
        self.assertEqual(len(r["rejected"]),1)
        self.assertEqual(r["snapshots"][0]["reserved_margin"],0)

if __name__=="__main__":
    unittest.main()
