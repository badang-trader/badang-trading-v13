"""Stage 93 regression tests for censored OHLC adverse excursion."""
import unittest
from unittest.mock import patch
from badang_censored_ohlc_stress import audit

class CensoredOhlcStressTests(unittest.TestCase):
    def test_long_uses_low_short_uses_high_and_keeps_close_separate(self):
        rows=[
            [1000,100,112,90,105,1],
            [2000,105,120,80,110,1],
            [3000,110,115,95,100,1],
        ]
        trades=[
            {"entry_bar":0,"exit_bar":2,"entry":100,"net_return":None,"exit_reason":"END_OF_DATA"},
            {"entry_bar":0,"exit_bar":2,"entry":100,"net_return":None,"exit_reason":"END_OF_DATA"},
        ]
        cases=[{"symbol":"BTC","timeframe":"1H","reversal_backtest":{
            "early":{"trades":trades},"confirmed":{"trades":[]}}}]
        samples=[
            {"trade_id":"early:BTC:1H:0","side":"LONG","net_return":None},
            {"trade_id":"early:BTC:1H:1","side":"SHORT","net_return":None},
        ]
        fake={"cutoff_ms":0,"results":[{"symbol":"BTC","timeframe":"1H",
              "strategy":"early","sample_entries":samples}]}
        with patch("badang_censored_ohlc_stress.ema_audit",return_value=fake):
            result=audit(cases,{("BTC","1H"):rows})
        self.assertEqual(result["censored_post_cutoff_count"],2)
        long,short=result["results"]
        self.assertAlmostEqual(long["worst_ohlc_adverse_return"],-.2)
        self.assertAlmostEqual(short["worst_ohlc_adverse_return"],-.2)
        self.assertAlmostEqual(long["last_close_return"],0.)
        self.assertAlmostEqual(short["last_close_return"],0.)
        self.assertTrue(result["no_account_level_intrabar_mdd"])
        self.assertTrue(result["no_liquidation_model"])

    def test_invalid_ohlc_rejected(self):
        rows=[[1000,100,95,105,100,1]]
        cases=[{"symbol":"ETH","timeframe":"1H","reversal_backtest":{
            "early":{"trades":[{"entry_bar":0,"exit_bar":0,"entry":100,
                               "net_return":None,"exit_reason":"END_OF_DATA"}]}}]
        fake={"cutoff_ms":0,"results":[{"symbol":"ETH","timeframe":"1H",
              "strategy":"early","sample_entries":[{"trade_id":"early:ETH:1H:0",
              "side":"LONG","net_return":None}]}]}
        with patch("badang_censored_ohlc_stress.ema_audit",return_value=fake):
            with self.assertRaises(AssertionError):
                audit(cases,{("ETH","1H"):rows})

if __name__=="__main__":
    unittest.main()
