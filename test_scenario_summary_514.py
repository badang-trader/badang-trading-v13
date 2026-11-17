import unittest
from badang_scenario_summary_514 import summarize_scenarios
def support(zones=None):
    return {"status":"ok","reference_close":100.0,"observation_zones":zones if zones is not None else [
        {"zone_lower":95.0,"zone_upper":97.0},{"zone_lower":89.0,"zone_upper":92.0}]}
class ScenarioSummaryTests(unittest.TestCase):
    def test_support_order_and_breakdown(self):
        d=summarize_scenarios(support([{"zone_lower":89,"zone_upper":92},{"zone_lower":95,"zone_upper":97}]),{"status":"ok","trend":"DOWN"})
        self.assertEqual(d["nearest_support"]["lower"],95)
        self.assertEqual(d["next_support_if_broken"]["lower"],89)
    def test_mixed_divergence_keeps_both_sides(self):
        d=summarize_scenarios(support(),{"status":"ok","trend":"UP"},{"status":"mixed"})
        self.assertTrue(any("RSI" in x for x in d["long_evidence"]))
        self.assertTrue(any("RSI" in x for x in d["short_evidence"]))
    def test_bad_support_data_fails_closed(self):
        d=summarize_scenarios({"status":"invalid_timestamp"},{"status":"ok"})
        self.assertEqual(d["status"],"data_warning")
    def test_nan_zone_excluded(self):
        d=summarize_scenarios(support([{"zone_lower":float("nan"),"zone_upper":97}]),{"status":"ok"})
        self.assertIsNone(d["nearest_support"])
    def test_no_invented_probability_or_trade(self):
        d=summarize_scenarios(support(),{"status":"ok","wave_candidates":[]})
        self.assertIsNone(d["rebound_probability"])
        self.assertIsNone(d["trade_signal"])
    def test_no_second_support(self):
        d=summarize_scenarios(support([{"zone_lower":95,"zone_upper":97}]),{"status":"ok"})
        self.assertIsNone(d["next_support_if_broken"])
    def test_untrusted_reference_price(self):
        d=summarize_scenarios({"status":"ok","reference_close":float("inf"),"observation_zones":[]},{"status":"ok"})
        self.assertEqual(d["status"],"data_warning")
if __name__=="__main__":
    unittest.main()
