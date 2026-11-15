"""Integrated audit must respect the final manual-review gate."""
import unittest
from badang_signal_audit_439 import reconcile


class FinalAuditGateTests(unittest.TestCase):
    def base(self):
        return {
            "candidate_side": "LONG", "exchange": "bitget",
            "data_quality": {"cross_exchange": False},
            "technical_side": "LONG", "trend_aligned": True,
            "signal_precision_418": {"status": "CANDIDATE"},
            "cvd_quality": "UNVERIFIED",
            "futures_data_available": {"oi_history": False},
        }

    def test_final_wait_cannot_be_review_only(self):
        item=self.base()
        item["decision_427"]={"state": "WAIT"}
        result=reconcile(item)
        self.assertEqual(result["status"], "WAIT")
        self.assertIn("최종 진입 판단 미통과 또는 미확인", result["reasons"])

    def test_missing_final_decision_cannot_be_review_only(self):
        result=reconcile(self.base())
        self.assertEqual(result["status"], "WAIT")

    def test_ready_review_remains_manual_only_with_flow_warnings(self):
        item=self.base()
        item["decision_427"]={"state": "READY_REVIEW"}
        result=reconcile(item)
        self.assertEqual(result["status"], "REVIEW_ONLY")
        self.assertFalse(result["order_authorized"])
        self.assertIn("전체 체결 CVD 미검증", result["missing_flow"])


if __name__ == "__main__":
    unittest.main()
