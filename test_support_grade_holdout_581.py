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
        self.assertEqual(strong["pre_outcome_mae_by_outcome"]["rebound"]["mean_pre_outcome_mae_pct"],0.2)
        self.assertEqual(strong["pre_outcome_mae_by_outcome"]["breakdown_on_touch"]["max_pre_outcome_mae_pct"],1.1)
        self.assertIsNone(strong["pre_outcome_mae_by_outcome"]["breakdown"]["mean_pre_outcome_mae_pct"])
        self.assertEqual(result["by_evidence_grade"]["moderate_evidence"]["breakdown"],1)
        self.assertEqual(result["by_evidence_grade"]["limited_evidence"]["resolved"],0)
        self.assertEqual(result["by_evidence_grade"]["ungraded"]["events"],0)

    def test_missing_and_unknown_grades_are_not_lost(self):
        events=[
            {"outcome":"rebound","pre_outcome_max_adverse_excursion_pct":0.2},
            {"outcome":"breakdown","evidence_grade_at_touch":"unknown","pre_outcome_max_adverse_excursion_pct":0.8},
            {"outcome":"unresolved","evidence_grade_at_touch":"limited_evidence","pre_outcome_max_adverse_excursion_pct":0.1},
        ]
        result=_summary(events,30)
        groups=result["by_evidence_grade"]
        self.assertEqual(sum(g["events"] for g in groups.values()),len(events))
        self.assertEqual(groups["ungraded"]["events"],2)
        self.assertEqual(groups["ungraded"]["resolved"],2)
        self.assertIsNone(groups["ungraded"]["rebound_fraction"])

    def test_pre_touch_regime_groups_preserve_all_events(self):
        events=[
            {"outcome":"rebound","regime_before_touch":"up",
             "pre_outcome_max_adverse_excursion_pct":0.2},
            {"outcome":"breakdown","regime_before_touch":"down",
             "pre_outcome_max_adverse_excursion_pct":1.0},
            {"outcome":"unresolved","regime_before_touch":"sideways",
             "pre_outcome_max_adverse_excursion_pct":0.4},
            {"outcome":"breakdown_on_touch",
             "pre_outcome_max_adverse_excursion_pct":1.2},
        ]
        result=_summary(events,30)["by_pre_touch_regime"]
        self.assertEqual(sum(g["events"] for g in result.values()),4)
        self.assertEqual(result["up"]["rebound"],1)
        self.assertEqual(result["up"]["pre_outcome_mae_by_outcome"]["rebound"]["mean_pre_outcome_mae_pct"],0.2)
        self.assertEqual(result["down"]["pre_outcome_mae_by_outcome"]["breakdown"]["max_pre_outcome_mae_pct"],1.0)
        self.assertEqual(result["unclassified"]["pre_outcome_mae_by_outcome"]["breakdown_on_touch"]["count"],1)
        for outcome in ("rebound","breakdown","breakdown_on_touch","unresolved"):
            self.assertEqual(
                sum(group["pre_outcome_mae_by_outcome"][outcome]["count"]
                    for group in result.values()),
                sum(e["outcome"] == outcome for e in events))
        self.assertEqual(result["down"]["breakdown"],1)
        self.assertEqual(result["sideways"]["resolved"],0)
        self.assertEqual(result["unclassified"]["breakdown"],1)
        self.assertTrue(all(g["rebound_fraction"] is None for g in result.values()))

    def test_probability_only_when_threshold_met(self):
        events=[{"outcome":"rebound" if i<18 else "breakdown",
                 "evidence_grade_at_touch":"strong_evidence",
                 "pre_outcome_max_adverse_excursion_pct":0.3} for i in range(30)]
        result=_summary(events,30)["by_evidence_grade"]["strong_evidence"]
        self.assertTrue(result["sample_adequate"])
        self.assertEqual(result["rebound_fraction"],0.6)

if __name__=="__main__": unittest.main()
