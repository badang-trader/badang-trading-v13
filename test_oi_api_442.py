import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
# Work under unittest discovery and pytest without hiding missing dependencies.
try:
    import flask
except ModuleNotFoundError as exc:
    if exc.name != 'flask':
        raise
    flask = None
if flask is not None:
    import app

@unittest.skipUnless(flask is not None, "Flask integration dependency is not installed")
class OIApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict("os.environ", {"BADANG_OI_COLLECTOR_TOKEN": "test-secret", "DATABASE_URL": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = app.app.test_client()
        app._OI_LAST_SAMPLE.clear()
        self.path = str(Path(self.temp.name) / 'history.db')
        self.patcher = patch.object(app, '_oi_db_path', return_value=self.path)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_get_missing(self):
        d = self.client.get('/api/oi-history-442?symbol=BTCUSDT').get_json()
        self.assertEqual(d['status'], 'INSUFFICIENT_HISTORY')
        self.assertFalse(d['continuous_collection'])
        self.assertFalse(d['used_in_trading_score'])

    def test_invalid_symbol(self):
        self.assertEqual(self.client.get('/api/oi-history-442?symbol=bad!').status_code, 400)

    def test_post_collect_and_rate_limit(self):
        with patch('bitget_market_data._get', return_value={'openInterestList':[{'size':'123'}]}):
            r = self.client.post('/api/oi-history-442?symbol=BTCUSDT', headers={'X-Badang-Collector-Token': 'test-secret'})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()['current_oi'], 123)
            self.assertEqual(self.client.post('/api/oi-history-442?symbol=BTCUSDT', headers={'X-Badang-Collector-Token': 'test-secret'}).status_code, 429)
        d = self.client.get('/api/oi-history-442?symbol=BTCUSDT').get_json()
        self.assertEqual(d['current_oi'], 123)
        self.assertIsNone(d['oi_change_15m_pct'])

    def test_post_without_token_is_forbidden(self):
        r = self.client.post('/api/oi-history-442?symbol=BTCUSDT')
        self.assertEqual(r.status_code, 403)

    def test_upstream_failure(self):
        with patch('bitget_market_data._get', side_effect=RuntimeError('offline')):
            self.assertEqual(self.client.post('/api/oi-history-442?symbol=ETHUSDT', headers={'X-Badang-Collector-Token': 'test-secret'}).status_code, 502)

if __name__ == '__main__':
    unittest.main()
