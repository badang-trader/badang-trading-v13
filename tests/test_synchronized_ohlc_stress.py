import unittest
from badang_synchronized_ohlc_stress import stress_snapshots

class SharedCloseStressTests(unittest.TestCase):
    def test_two_positions_same_close_use_adverse_extremes(self):
        histories={
            ("BTC","1H"):[[0,100,110,90,100,1]],
            ("ETH","1H"):[[0,100,120,80,100,1]]}
        snap={"ts":3600000,"realized_pnl":0.,
              "strict_observed_equity":10000.,
              "active_positions":[
                  {"symbol":"BTC","timeframe":"1H","side":"LONG",
                   "entry_price":100.,"margin":500.,"leverage":2},
                  {"symbol":"ETH","timeframe":"1H","side":"SHORT",
                   "entry_price":100.,"margin":500.,"leverage":2}]}
        out=stress_snapshots([snap],histories)
        self.assertEqual(out["exact_observations"],1)
        self.assertAlmostEqual(out["worst_observation"]["stress_equity"],9700.)
        self.assertAlmostEqual(out["synchronized_ohlc_stress_mdd"],.03)
    def test_missing_shared_close_is_skipped_not_forward_filled(self):
        histories={("BTC","1H"):[[0,100,110,90,100,1]]}
        snap={"ts":7200000,"realized_pnl":0.,"strict_observed_equity":10000.,
              "active_positions":[{"symbol":"BTC","timeframe":"1H","side":"LONG",
                   "entry_price":100.,"margin":500.,"leverage":2}]}
        out=stress_snapshots([snap],histories)
        self.assertEqual(out["status"],"NO_EXACT_SHARED_CLOSE")
        self.assertIsNone(out["synchronized_ohlc_stress_mdd"])

if __name__=="__main__":
    unittest.main()
