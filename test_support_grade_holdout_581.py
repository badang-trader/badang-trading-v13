"""Evidence-grade holdout summaries must not turn small samples into probabilities."""
import unittest
from badang_support_holdout_550 import _summary

class EvidenceGradeHoldoutTests(unittest.TestCase):
    def test_counts_and_minimum_sample_gate(self):
        events=[
            {"outcome":"rebound","evidence_grade_at_touch":"strong_evidence","pre_outcome_max_adverse_excursion_pct":0.2},
            {"outcome":"breakdown_on_touch","evidence_grade_at_touch":"strong_evidence","pre_outcome_max_adverse_excursion_pct":1.1},
            {"outcome":"breakdown","evidence_grade_at_touch":"moderate_evidence","pre_outcome_max_adverse_excursion_pct":0.7},
            {"outcome":"unresolved","evidence_grade_at_touch":"limited_evidence","pre_outcome_max_adverse_excursion_pct":0.1},
        ]
        result=_summary(events,30)
        strong=result["by_evidence_grade"]["strong_evidence"]
        self.assertEqual((strong["rebound"],strong["breakdown"],strong["resolved"]),(1,1,2))
        self.assertIsNone(strong["rebound_fraction"])
        self.assertFalse(strong["sample_adequate"])
        self.assertEqual(result["by_evidence_grade"]["moderate_evidence"]["breakdown"],1)
        self.assertEqual(result["by_evidence_grade"]["limited_evidence"]["resolved"],0)
        self.assertEqual(result["by_evidence_grade"][None]["events"],0)

    def test_probability_only_when_threshold_met(self):
        events=[{"outcome":"rebound" if i<18 else "breakdown",
                 "evidence_grade_at_touch":"strong_evidence",
                 "pre_outcome_max_adverse_excursion_pct":0.3} for i in range(30)]
        result=_summary(events,30)["by_evidence_grade"]["strong_evidence"]
        self.assertTrue(result["sample_adequate"])
        self.assertEqual(result["rebound_fraction"],0.6)

if __name__=="__main__": unittest.main()
