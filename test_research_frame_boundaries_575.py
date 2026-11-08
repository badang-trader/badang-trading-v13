"""Check UTC calendar boundaries and frame mismatch in historical candles."""
import unittest
from datetime import datetime,timezone,timedelta
from badang_research_timestamp_validation_569 import validate_research_timestamps

def ms(dt):
    return int(dt.timestamp()*1000)
def bars(*dates):
    return [{"timestamp":ms(d)} for d in dates]

class FrameBoundaryTests(unittest.TestCase):
    def test_fifteen_minute_utc_midnight_rollover(self):
        t=datetime(2026,11,8,23,45,tzinfo=timezone.utc)
        self.assertTrue(validate_research_timestamps(bars(t,t+timedelta(minutes=15),t+timedelta(minutes=30)),900000))
    def test_daily_utc_month_boundary(self):
        t=datetime(2026,10,31,tzinfo=timezone.utc)
        self.assertTrue(validate_research_timestamps(bars(t,t+timedelta(days=1),t+timedelta(days=2)),86400000))
    def test_daily_utc_year_boundary(self):
        t=datetime(2026,12,31,tzinfo=timezone.utc)
        self.assertTrue(validate_research_timestamps(bars(t,t+timedelta(days=1)),86400000))
    def test_fifteen_minute_bars_rejected_as_daily(self):
        t=datetime(2026,11,8,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            validate_research_timestamps(bars(t,t+timedelta(minutes=15)),86400000)
    def test_daily_bars_rejected_as_fifteen_minute(self):
        t=datetime(2026,11,8,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            validate_research_timestamps(bars(t,t+timedelta(days=1)),900000)
    def test_missing_midnight_interval_rejected(self):
        t=datetime(2026,11,8,23,45,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            validate_research_timestamps(bars(t,t+timedelta(minutes=30)),900000)
if __name__=="__main__":unittest.main()
