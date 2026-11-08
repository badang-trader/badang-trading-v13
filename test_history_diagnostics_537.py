"""History diagnostic must distinguish exhausted pagination from successful history."""
import unittest
from unittest.mock import patch
from bitget_market_data import fastest_candles

class HistoryDiagnosticsTests(unittest.TestCase):
    def test_empty_history_page_reports_stop_reason(self):
        step=86400000
        now=1760000000000
        newest=(now//step-1)*step
        page=[[str(newest-i*step),"100","101","99","100","10"] for i in range(89)]
        with patch("bitget_market_data.time.time",return_value=now/1000),patch("bitget_market_data._get",side_effect=[page,[]]) as get:
            with self.assertRaisesRegex(ValueError,"history_stop=empty_history_page") as caught:
                fastest_candles("SOXLUSDT","1D")
            self.assertIn("history_pages=1",str(caught.exception))
            self.assertEqual(get.call_count,2)

if __name__=="__main__":unittest.main()
