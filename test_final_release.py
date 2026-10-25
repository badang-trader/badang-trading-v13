import ast, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parent
class ReleaseTests(unittest.TestCase):
 def test_all_python_parse(self):
  for f in ROOT.glob('*.py'):
   with self.subTest(f=f.name):ast.parse(f.read_text())
 def test_modes(self):
  s=(ROOT/'app.py').read_text()
  self.assertIn("['15m', '30m', '1H']",s)
  self.assertIn("['1H', '4H', '1D']",s)
 def test_flow_guard(self):
  s=(ROOT/'app.py').read_text()
  self.assertIn("'data_caveats'",s)
  self.assertIn("item['recommendation'] = 'WAIT'",s)
 def test_technical_modules(self):
  s=(ROOT/'badang_analysis_v13.py').read_text()
  for name in ['def divergence_details(', 'def wave_candidates(', 'def analyze(']:self.assertIn(name,s)
if __name__=='__main__':unittest.main()
