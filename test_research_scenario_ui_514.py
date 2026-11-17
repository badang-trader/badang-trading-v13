"""Research page must show the new scenario above the old technical output."""
import unittest
from badang_research_ui import app
class ResearchScenarioUiTests(unittest.TestCase):
    def test_ui_has_scenario_section(self):
        response=app.test_client().get("/research")
        self.assertEqual(response.status_code,200)
        html=response.get_data(as_text=True)
        self.assertIn('id="scenario-summary"',html)
        self.assertIn("out.innerHTML=scHtml+",html)
        self.assertIn("scenario_summary",html)
    def test_user_provided_evidence_is_escaped(self):
        html=app.test_client().get("/research").get_data(as_text=True)
        self.assertIn("map(x=>'<li>'+esc(x)+'</li>')",html)
        self.assertIn("esc(sc.headline",html)
    def test_original_scanner_home_route_preserved(self):
        routes={rule.rule for rule in app.url_map.iter_rules()}
        self.assertIn("/",routes)
        self.assertIn("/api/scan",routes)
        self.assertIn("/api/research-514",routes)
if __name__=="__main__":
    unittest.main()
