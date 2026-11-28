import unittest
from unittest.mock import patch
from badang_trade_config_460 import poll_interval_ms, poll_interval_seconds
from badang_trade_runner_457 import interval_from_env

class TestSharedPollConfig(unittest.TestCase):
    def test_default(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(poll_interval_ms(), 60000)
            self.assertEqual(interval_from_env(), 60)
    def test_custom_shared(self):
        with patch.dict('os.environ', {'BADANG_TRADE_POLL_SECONDS':'120'}):
            self.assertEqual(poll_interval_ms(), 120000)
            self.assertEqual(interval_from_env(), 120)
    def test_boundaries(self):
        self.assertEqual(poll_interval_seconds('15'), 15)
        self.assertEqual(poll_interval_seconds('3600'), 3600)
    def test_invalid(self):
        for value in ('nan','inf','14','3601','0','60.5','abc',True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                poll_interval_seconds(value)
    def test_status_uses_worker_config(self):
        from badang_trade_status_458 import collection_status
        fake={'symbol':'BTCUSDT','source_exchange':'bitget','snapshot_count':2,'latest_age_ms':1000,'largest_collection_gap_ms':90000}
        with patch('badang_trade_status_458.status',return_value=fake), patch.dict('os.environ', {'BADANG_TRADE_POLL_SECONDS':'120'}):
            out=collection_status('BTCUSDT')
        self.assertEqual(out['expected_poll_ms'],120000)
        self.assertEqual(out['quality_status'],'SNAPSHOTS_REGULAR')
        self.assertFalse(out['restart_recovery_verified'])
        self.assertFalse(out['is_cvd'])

if __name__=='__main__': unittest.main()
