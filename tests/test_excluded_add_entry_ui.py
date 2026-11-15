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

    def test_structure_and_wave_panel_remain(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("function unifiedPanel427(x)", source)
        self.assertIn("${unifiedPanel427(x)}", source)
        self.assertIn("function card(x)", source)


if __name__ == "__main__":
    unittest.main()
