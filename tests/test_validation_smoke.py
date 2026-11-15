import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ValidationSmokeTests(unittest.TestCase):
    def test_application_syntax(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        ast.parse(source)

    def test_signal_validation_functions_exist(self):
        tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
        names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for required in ("extract_v13_signal", "get_reference_time", "save_signals", "ensure_database"):
            with self.subTest(function=required):
                self.assertIn(required, names)

    def test_runtime_dependencies_declared(self):
        reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        for package in ("flask", "requests", "psycopg2"):
            with self.subTest(package=package):
                self.assertIn(package, reqs)

if __name__ == "__main__":
    unittest.main()
