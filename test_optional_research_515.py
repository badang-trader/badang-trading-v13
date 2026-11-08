import unittest
from badang_optional_research_515 import evaluate_optional_research


class OptionalResearchTests(unittest.TestCase):
    def test_missing_function_explicitly_unavailable(self):
        result = evaluate_optional_research(None, {"exchange": "bitget"}, [])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["reason"], "OPTIONAL_RESEARCH_NOT_INSTALLED")
        self.assertFalse(result["eligible_for_alert"])
        self.assertIsNone(result["sample_imbalance"])
        self.assertEqual(result["trade_sample_count"], 0)

    def test_valid_function_is_used(self):
        result = evaluate_optional_research(
            lambda item, candles: {"status": "OK", "trade_sample_count": 40},
            {}, [],
        )
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["trade_sample_count"], 40)

    def test_broken_function_fails_closed(self):
        def broken(item, candles):
            raise RuntimeError("test failure")
        result = evaluate_optional_research(broken, {}, [])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["reason"], "OPTIONAL_RESEARCH_FAILED")

    def test_non_mapping_result_fails_closed(self):
        result = evaluate_optional_research(lambda item, candles: None, {}, [])
        self.assertEqual(result["reason"], "OPTIONAL_RESEARCH_FAILED")


if __name__ == "__main__":
    unittest.main()
