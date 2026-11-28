"""First observable time must be after right-side pivot confirmation bars."""
import unittest
from app import explain_rsi_divergences_46
from test_divergence_real_pipeline_514 import bars

class ObservableTimeTests(unittest.TestCase):
    def test_no_lookahead_in_pivot_confirmation(self):
        signals = explain_rsi_divergences_46(bars(), "1H")
        for signal in signals:
            self.assertEqual(signal["first_observable_time"] - signal["second_time"],
                             signal["pivot_confirmation_bars"] * 3600000)
            self.assertGreater(signal["first_observable_bar_index"], 0)
    def test_no_future_confirmation_at_snapshot(self):
        for count in (60, 90, 120, 180, 260):
            sample = bars(count)
            signals = explain_rsi_divergences_46(sample, "1H")
            last_closed_open = int(sample[-2][0])
            for signal in signals:
                self.assertLessEqual(signal["first_observable_time"], last_closed_open)
    def test_timestamp_is_not_pivot_timestamp(self):
        for signal in explain_rsi_divergences_46(bars(), "1H"):
            self.assertGreater(signal["first_observable_time"], signal["second_time"])
if __name__ == "__main__":
    unittest.main()
