import unittest
from badang_divergence_clarity_514 import explain_conflict
def s(t,status="RECENT_UNCONFIRMED_REVERSAL",recent=True,pivot_confirmed=True):
    return {"type":t,"status":status,"recent":recent,"pivot_confirmed":pivot_confirmed,"timeframe":"1H","second_time":1}
class DivergenceClarityTests(unittest.TestCase):
    def test_mixed(self):
        d=explain_conflict([s("hidden_bearish"),s("regular_bullish")])
        self.assertEqual(d["status"],"mixed")
        self.assertEqual(len(d["items"]),2)
    def test_old_and_invalidated_not_current(self):
        d=explain_conflict([s("hidden_bearish","HISTORICAL"),s("regular_bullish","INVALIDATED")])
        self.assertEqual(d["status"],"no_current_signal")
    def test_single_bullish(self):
        self.assertEqual(explain_conflict([s("regular_bullish")])["status"],"bullish_observation")
    def test_unconfirmed_pivot_excluded(self):
        self.assertEqual(explain_conflict([s("regular_bullish",pivot_confirmed=False)])["status"],"no_current_signal")
    def test_malformed(self):
        self.assertEqual(explain_conflict(None)["status"],"invalid_input")
    def test_unknown_signal_ignored(self):
        self.assertEqual(explain_conflict([s("fake")])["status"],"no_current_signal")
if __name__=="__main__":
    unittest.main()
