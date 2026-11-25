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
        self.assertIn("n(rr1,2)", source)
        self.assertIn("fmt(plan.tp2)", source)

    def test_scanner_card_requires_final_manual_gate(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("const finalReady=x.decision_427?.state===\\'READY_REVIEW\\'", source)
        self.assertIn("x.integrated_audit_439?.status===\\'REVIEW_ONLY\\'", source)
        self.assertIn("const ready=d.state", source)
        self.assertIn("const plan=finalReady?", source)
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
        self.assertIn("'slippage_assumption_roundtrip_pct':ROUNDTRIP_SLIPPAGE_PCT", body)
        self.assertIn("execution_cost = entry * (ROUNDTRIP_FEE_PCT + ROUNDTRIP_SLIPPAGE_PCT) / 100", body)

    def test_price_action_plan_can_clear_its_own_net_reward_gate(self):
        from app import build_decision_plan_425, price_action_45

        rows = [[i, 100, 100.3, 99.7, 100, 10] for i in range(45)]
        rows += [[45, 100, 100.8, 99.9, 100.75, 15], rows[-1]]
        action = price_action_45(rows, {'1H': 'UP', '30m': 'UP'}, 'scalp')
        self.assertEqual(action['side'], 'LONG')
        plan = build_decision_plan_425({'long_score': 85, 'short_score': 50},
                                       action, {'status': 'CANDIDATE'}, 'scalp')
        self.assertEqual(plan['state'], 'READY_REVIEW')
        self.assertAlmostEqual(plan['rr1_net_estimate'], 1.5)
        self.assertAlmostEqual(plan['rr2_net_estimate'], 2.0)

    def test_scan_offset_rejects_malformed_input(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("if not re.fullmatch(r'[0-9]{1,8}', offset_raw):", source)
        self.assertIn("return jsonify(error='offset은 0 이상의 정수여야 합니다'), 400", source)

    def test_trend_alignment_requires_all_required_frames(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("all(tf in trends and trends[tf] == expected_trend", source)

    def test_decision_panel_respects_final_gate_and_hides_add_entry(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        start = source.index("function decisionPanel425(x)")
        end = source.index("function unifiedPanel427(x)", start)
        panel = source[start:end]
        self.assertNotIn("추가 진입:", panel)
        self.assertNotIn("p.add_condition", panel)
        self.assertIn("최종 보류 · 진입 검토 불가", panel)
        self.assertIn("x.integrated_audit_439?.status", panel)
        self.assertIn("슬리피지 가정", panel)

    def test_structure_and_wave_panel_remain(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("function unifiedPanel427(x)", source)
        self.assertIn("${unifiedPanel427(x)}", source)
        self.assertIn("function card(x)", source)


if __name__ == "__main__":
    unittest.main()
