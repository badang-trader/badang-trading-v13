"""Dashboard UI regression checks: no exchange access or orders."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "badang_dashboard.py").read_text(encoding="utf-8")

class DashboardClarityTests(unittest.TestCase):
    def test_structured_divergence_only(self):
        self.assertIn("Array.isArray(signals)", SOURCE)
        self.assertIn("z.status==='RECENT_UNCONFIRMED_REVERSAL'", SOURCE)
        self.assertIn("z.pivot_confirmed===true", SOURCE)
        self.assertIn("z.confirmed===false", SOURCE)
        self.assertNotIn("JSON.stringify(val||{}).toLowerCase()", SOURCE)

    def test_user_explanations_and_no_orders(self):
        for phrase in ("바당의 쉬운 판단", "진입 대기", "반전 미확정", "혼재", "손절 기준"):
            self.assertIn(phrase, SOURCE)
        self.assertIn("자동매매 아님", SOURCE)

    def test_embedded_javascript_syntax(self):
        if not shutil.which("node"):
            self.skipTest("Node.js not available")
        scripts = re.findall(r"<script>(.*?)</script>", SOURCE, flags=re.S)
        self.assertEqual(len(scripts), 1)
        with tempfile.TemporaryDirectory() as directory:
            js = pathlib.Path(directory) / "dashboard.js"
            js.write_text(scripts[0], encoding="utf-8")
            run = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)

if __name__ == "__main__":
    unittest.main()
