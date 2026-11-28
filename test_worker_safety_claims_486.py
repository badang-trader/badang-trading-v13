"""Fail closed on unsupported CVD or order-readiness claims in sample diagnostics."""
import unittest
from unittest.mock import patch
from badang_worker_crosscheck_483 import crosscheck
from test_worker_crosscheck_483 import Connection, NOW


def sample(name):
    return {'symbol': name, 'status': 'TWO_RECENT_SAMPLES_ONLY',
            'latest_fetched_ms': 98500}


def check(progress):
    with patch('badang_worker_crosscheck_483.symbols_from_env', return_value=['BTCUSDT', 'ETHUSDT']):
        return crosscheck(lambda: progress, lambda: Connection([(98000, 99000, 'ok')]), NOW, 5000)


class Tests(unittest.TestCase):
    def base(self):
        return {'status': 'ALL_TWO_RECENT_SAMPLES_ONLY',
                'symbols': [sample('BTCUSDT'), sample('ETHUSDT')]}

    def test_normal_sample_report_is_only_a_sample(self):
        r = check(self.base())
        self.assertEqual(r['status'], 'RECENT_SAMPLES_AND_WORKER_ONLY')
        self.assertFalse(r['safe_to_enable_orders'])

    def test_top_level_unsupported_flags_fail_closed(self):
        for flag in ('coverage_confirmed', 'continuous_cvd_verified',
                     'trading_ready', 'safe_to_enable_orders'):
            with self.subTest(flag=flag):
                p = self.base()
                p[flag] = True
                r = check(p)
                self.assertEqual(r['status'], 'UNSUPPORTED_READINESS_CLAIM')
                self.assertFalse(r['safe_to_enable_orders'])

    def test_symbol_unsupported_flags_fail_alignment(self):
        for flag in ('coverage_confirmed', 'continuous_cvd_verified',
                     'trading_ready', 'safe_to_enable_orders', 'is_cvd'):
            with self.subTest(flag=flag):
                p = self.base()
                p['symbols'][0][flag] = True
                r = check(p)
                self.assertEqual(r['status'], 'WORKER_OR_SNAPSHOT_WARNING')
                self.assertFalse(r['latest_run_snapshot_aligned'])

if __name__ == '__main__':
    unittest.main()
