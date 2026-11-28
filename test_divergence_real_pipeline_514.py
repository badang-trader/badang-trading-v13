"""Regression tests against the original scanner's divergence output."""
import unittest
from app import explain_rsi_divergences_46
from badang_divergence_clarity_514 import explain_conflict

def bars(n=260, start=1700002800000):
    out=[]
    for i in range(n):
        # deterministic wave-like OHLCV with exactly one-hour spacing
        import math
        p=30000+90*math.sin(i/6)+i*0.5
        out.append([str(start+i*3600000),str(p),str(p+10),str(p-10),str(p),str(100+i%11)])
    return out

class PipelineTests(unittest.TestCase):
    def test_explained_signals_are_valid_classification_input(self):
        sig=explain_rsi_divergences_46(bars(),"1H")
        d=explain_conflict(sig)
        self.assertIn(d["status"],("mixed","bullish_observation","bearish_observation","no_current_signal"))
        self.assertTrue(all(s["type"] in ("regular_bullish","regular_bearish","hidden_bullish","hidden_bearish") for s in d["items"]))
    def test_latest_unclosed_candle_cannot_change_signal(self):
        original=bars()
        changed=[r[:] for r in original]
        changed[-1][2]=str(float(changed[-1][2])*2)
        changed[-1][3]=str(float(changed[-1][3])/2)
        a=explain_rsi_divergences_46(original,"1H")
        b=explain_rsi_divergences_46(changed,"1H")
        self.assertEqual(a,b)
    def test_old_signal_does_not_force_mixed(self):
        current={"type":"regular_bullish","status":"RECENT_UNCONFIRMED_REVERSAL","pivot_confirmed":True,"recent":True}
        old={"type":"hidden_bearish","status":"HISTORICAL","pivot_confirmed":True,"recent":False}
        self.assertEqual(explain_conflict([current,old])["status"],"bullish_observation")
    def test_invalidated_signal_does_not_force_mixed(self):
        current={"type":"regular_bullish","status":"RECENT_UNCONFIRMED_REVERSAL","pivot_confirmed":True,"recent":True}
        invalid={"type":"hidden_bearish","status":"INVALIDATED","pivot_confirmed":True,"recent":True}
        self.assertEqual(explain_conflict([current,invalid])["status"],"bullish_observation")
    def test_never_claims_buy_or_sell(self):
        sig=[{"type":"hidden_bearish","status":"RECENT_UNCONFIRMED_REVERSAL","pivot_confirmed":True,"recent":True},
             {"type":"regular_bullish","status":"RECENT_UNCONFIRMED_REVERSAL","pivot_confirmed":True,"recent":True}]
        d=explain_conflict(sig)
        self.assertNotIn("留ㅼ닔 ?뺤젙",str(d))
        self.assertNotIn("留ㅻ룄 ?뺤젙",str(d))
if __name__=="__main__":
    unittest.main()
