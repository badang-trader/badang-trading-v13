import unittest
from badang_trade_quality_459 import evaluate

class TestTradeQuality(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(evaluate({'snapshot_count':0,'latest_age_ms':None,'largest_collection_gap_ms':None})['quality_status'],'NO_RECORDS')
    def test_stale(self):
        self.assertEqual(evaluate({'snapshot_count':3,'latest_age_ms':150000,'largest_collection_gap_ms':60000})['quality_status'],'STALE')
    def test_gap(self):
        self.assertEqual(evaluate({'snapshot_count':3,'latest_age_ms':1000,'largest_collection_gap_ms':130000})['quality_status'],'GAP_DETECTED')
    def test_regular_is_not_complete(self):
        x=evaluate({'snapshot_count':3,'latest_age_ms':1000,'largest_collection_gap_ms':60000})
        self.assertEqual(x['quality_status'],'SNAPSHOTS_REGULAR')
        self.assertFalse(x['coverage_confirmed'])
        self.assertFalse(x['is_cvd'])
    def test_one_sample(self):
        self.assertEqual(evaluate({'snapshot_count':1,'latest_age_ms':1000,'largest_collection_gap_ms':None})['quality_status'],'INSUFFICIENT_HISTORY')
    def test_future_clock(self):
        self.assertEqual(evaluate({'snapshot_count':2,'latest_age_ms':-100,'largest_collection_gap_ms':60000})['quality_status'],'CLOCK_ANOMALY')
    def test_bad_config(self):
        with self.assertRaises(ValueError): evaluate({},expected_poll_ms=0)
    def test_boolean_not_int(self):
        with self.assertRaises(ValueError): evaluate({'snapshot_count':True},expected_poll_ms=60000)

if __name__=='__main__': unittest.main()
