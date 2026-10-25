from pathlib import Path
import ast
import unittest
ROOT = Path(__file__).resolve().parent
class ReleaseTests(unittest.TestCase):
    def test_all_python_parses(self):
        for path in ROOT.glob('*.py'):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding='utf-8'))
    def test_modes_and_guard(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn("['15m', '30m', '1H']",source)
        self.assertIn("['1H', '4H', '1D']",source)
        self.assertIn('TECHNICAL_CANDIDATE_NOT_EXECUTION_ORDER',source)
        self.assertIn('coverage_confirmed',source)
    def test_ui_matches(self):
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('단타 · 15분 / 30분 / 1시간',source)
if __name__=='__main__': unittest.main()
