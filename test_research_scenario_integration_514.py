"""Research API integration regression with mocked trusted exchange history."""
import unittest
from unittest.mock import patch
from badang_research_ui import app

class ResearchScenarioIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
    def test_research_includes_combined_scenario(self):
        candles=[[str(i*3600000),"100","101","99","100","10"] for i in range(600)]
        history={"status":"ok","candles":candles,"source":"mocked"}
        support={"status":"ok","reference_close":100.0,"observation_zones":[{"zone_lower":95,"zone_upper":97}],"warnings":[]}
        analysis={"status":"ok","trend":"UP","wave_candidates":[]}
        with patch("badang_research_ui.bitget_server_clock_ms",return_value=1794888000000),patch("badang_research_ui.research_history",return_value=history),patch("badang_research_ui.support_decision_map",return_value=support),patch("badang_research_ui.analyze",return_value=analysis),patch("badang_research_ui.approximate_volume_profile",return_value={"poc":100,"method":"estimate"}),patch("badang_research_ui.regime_at",return_value="UP"):
            response=self.client.get("/api/research-514?symbol=BTC&frame=1h")
        self.assertEqual(response.status_code,200)
        data=response.get_json()
        self.assertEqual(data["scenario_summary"]["status"],"observation_only")
        self.assertEqual(data["scenario_summary"]["nearest_support"]["lower"],95)
        self.assertIsNone(data["scenario_summary"]["trade_signal"])
    def test_rejected_symbol_has_no_scenario(self):
        response=self.client.get("/api/research-514?symbol=FAKE&frame=1h")
        self.assertEqual(response.status_code,400)
        self.assertNotIn("scenario_summary",response.get_json())
if __name__=="__main__":
    unittest.main()
