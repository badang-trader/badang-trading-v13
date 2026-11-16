"""Regression coverage for integrated home HTTP response preservation."""
import unittest
from flask import make_response
import badang_research_ui as research

class IntegratedHomeResponseTests(unittest.TestCase):
    def setUp(self):
        self.original = research._original_home

    def tearDown(self):
        research._original_home = self.original

    def test_preserves_html_headers_and_cookies(self):
        def home():
            r = make_response("<html><body>scanner</body></html>")
            r.headers["X-Scanner"] = "preserved"
            r.set_cookie("scanner", "yes", httponly=True)
            return r
        research._original_home = home
        with research.app.app_context():
            result = research.integrated_home()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["X-Scanner"], "preserved")
        self.assertIn("scanner=yes", result.headers["Set-Cookie"])
        self.assertIn("scanner", result.get_data(as_text=True))
        self.assertIn('id="badang514"', result.get_data(as_text=True))

    def test_does_not_modify_non_html_or_error(self):
        for status, mime in [(302, "text/html"), (503, "text/html"), (200, "application/json")]:
            with self.subTest(status=status, mime=mime):
                research._original_home = lambda: (('{"ok":false}' if mime == "application/json" else "unavailable"), status, {"Content-Type": mime})
                with research.app.app_context():
                    result = research.integrated_home()
                self.assertEqual(result.status_code, status)
                self.assertNotIn('id="badang514"', result.get_data(as_text=True))

if __name__ == "__main__":
    unittest.main()
