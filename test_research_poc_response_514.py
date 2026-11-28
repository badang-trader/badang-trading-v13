"""Research API POC response regression: display numeric price, never object."""
import unittest
from unittest.mock import patch
import badang_research_ui as ui


class ResearchPocResponseTests(unittest.TestCase):
    def _request(self, poc):
        bars = [[str(1700000000000 + i * 3600000), "100", "102", "99", "101", "12"] for i in range(600)]
        history = {"status": "ok", "candles": bars, "source": "test"}
        decision = {"status": "ok", "observation_zones": [], "warnings": []}
        profile = {"status": "ok", "poc": poc, "method": "estimated"}
        with patch.object(ui, "research_history", return_value=history), \
             patch.object(ui, "support_decision_map", return_value=decision), \
             patch.object(ui, "analyze", return_value={"status": "ok"}), \
             patch.object(ui, "approximate_volume_profile", return_value=profile), \
             patch.object(ui, "regime_at", return_value="sideways"), \
             ui.app.test_request_context("/api/research-514?symbol=BTC&frame=1h"):
            return ui.app.make_response(ui.research_514())

    def test_poc_is_numeric_price_not_dictionary(self):
        response = self._request({"lower": 100.0, "upper": 101.0, "center": 100.5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["volume_profile_poc"], 100.5)

    def test_missing_poc_is_null_not_crash(self):
        response = self._request(None)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["volume_profile_poc"])


if __name__ == "__main__":
    unittest.main()
