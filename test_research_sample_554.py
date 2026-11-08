"""Sample adequacy must not be mistaken for proven profitability."""
import unittest
from badang_research_sample_554 import assess_sample

class SampleAdequacyTests(unittest.TestCase):
    def test_short_history_and_sparse_trades_warn(self):
        result=assess_sample(2,220)
        self.assertFalse(result["sample_adequate_for_preliminary_review"])
        self.assertFalse(result["profitability_verified"])
        self.assertEqual(len(result["warnings"]),2)
    def test_sufficient_sample_still_does_not_prove_profit(self):
        result=assess_sample(100,5000)
        self.assertTrue(result["sample_adequate_for_preliminary_review"])
        self.assertFalse(result["profitability_verified"])
        self.assertEqual(result["warnings"],[])
    def test_invalid_inputs_fail_closed(self):
        for args in ((-1,300),(1,-1),(True,500),(1,500,0,10),(1,500,10,0)):
            with self.subTest(args=args),self.assertRaises(ValueError):
                assess_sample(*args)
if __name__=="__main__":unittest.main()
