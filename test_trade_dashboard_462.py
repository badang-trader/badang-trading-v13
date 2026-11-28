"""Static wiring regression checks, not a live integration test."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class WorkerDashboardWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app.py').read_text(encoding='utf-8')
        cls.tree = ast.parse(cls.source)

    def test_worker_endpoint_present(self):
        self.assertIn("@app.route('/api/trade-worker-462')", self.source)

    def test_worker_endpoint_disallows_cvd_and_scoring(self):
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'trade_worker_462')
        code = ast.get_source_segment(self.source, fn)
        for key in ('coverage_confirmed', 'used_in_trading_score', 'is_cvd'):
            self.assertIn("result['" + key + "'] = False", code)

    def test_dashboard_refresh_wired(self):
        self.assertIn('refreshTradeStore458(sym);refreshWorker462();', self.source)
        self.assertIn('id="worker462status"', self.source)

    def test_worker_status_not_trade_signal(self):
        self.assertIn('재시작 복구 미검증', self.source)
        self.assertIn('매매 점수 미반영', self.source)


if __name__ == '__main__':
    unittest.main()
