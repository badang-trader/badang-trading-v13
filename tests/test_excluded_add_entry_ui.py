"""Regression checks for explicitly excluded averaging-down UI.

Static source checks only; no network, live trading, or server startup.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ExcludedAddEntryUiTests(unittest.TestCase):
    def test_removed_calculator_is_not_rendered(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        for forbidden in ("function addEntryPanel426(", "function calcAddEntry426(",
                          "${addEntryPanel426(x)}", "add-calculate"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_decision_wave_scenarios_reach_manual_ui(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("item['decision_427'] = decision_review(", source)
        self.assertIn("d.wave_scenarios", source)
        self.assertIn("scenarioText", source)
        self.assertIn("무효화", source)

    def test_price_action_targets_do_not_claim_fixed_reward_risk(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("1차 목표 · 1.3R", source)
        self.assertNotIn("2차 목표 · 1.8R", source)
        self.assertIn("n(a.rr1,2)", source)
        self.assertIn("n(a.rr2,2)", source)

    def test_scanner_card_requires_final_manual_gate(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("const finalReady=x.decision_427?.state===\\'READY_REVIEW\\'", source)
        self.assertIn("x.integrated_audit_439?.status===\\'REVIEW_ONLY\\'", source)
        self.assertIn("const d=finalReady?candidate:\\'WAIT\\'", source)
        self.assertIn("최종 보류", source)

    def test_api_recommendations_require_both_final_gates(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("recommendations=top_five([item for item in results", source)
        self.assertIn("item.get('decision_427',{}).get('state')=='READY_REVIEW'", source)
        self.assertIn("item.get('integrated_audit_439',{}).get('status')=='REVIEW_ONLY'", source)

    def test_decision_plan_excludes_add_entry_fields_and_models_slippage(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        start = source.index("def build_decision_plan_425(")
        end = source.index("def scan_one(", start)
        body = source[start:end]
        self.assertNotIn("'add_entry':", body)
        self.assertNotIn("'add_condition':", body)
        self.assertIn("'slippage_assumption_roundtrip_pct':0.10", body)
        self.assertIn("execution_cost=entry*(0.0012+0.0010)", body)

    def test_scan_offset_rejects_malformed_input(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("if not re.fullmatch(r'[0-9]{1,8}', offset_raw):", source)
        self.assertIn("return jsonify(error='offset은 0 이상의 정수여야 합니다'), 400", source)

    def test_trend_alignment_requires_all_required_frames(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("all(tf in trends and trends[tf] == expected_trend", source)

    def test_structure_and_wave_panel_remain(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("function unifiedPanel427(x)", source)
        self.assertIn("${unifiedPanel427(x)}", source)
        self.assertIn("function card(x)", source)


if __name__ == "__main__":
    unittest.main()
