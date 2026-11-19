"""Feed integrity regression: forming bar excluded; invalid closed candles rejected."""
import unittest
from unittest.mock import patch
from app import candles

def sample():
    rows=[[str(i*900000),'100','105','95','101','10'] for i in range(205)]
    rows.append([str(205*900000),'100','105','95','101','10'])
    return rows

class ClosedFeedIntegrityTests(unittest.TestCase):
    def load(self,rows):
        with patch('bitget_market_data.fastest_candles',return_value={'candles':rows}):
            return candles('BTCUSDT','15m')

    def test_last_forming_bar_is_excluded(self):
        rows=sample()
        rows[-1][4]='999999'
        self.assertEqual(len(self.load(rows)),205)
        self.assertEqual(self.load(rows)[-1][4],'101')

    def test_duplicate_closed_timestamp_rejected(self):
        rows=sample()
        rows[100][0]=rows[99][0]
        with self.assertRaisesRegex(ValueError,'중복'):
            self.load(rows)

    def test_unsorted_closed_timestamp_rejected(self):
        rows=sample()
        rows[100][0]=str(98*900000)
        with self.assertRaisesRegex(ValueError,'역순'):
            self.load(rows)

    def test_invalid_ohlc_rejected(self):
        rows=sample()
        rows[100][2]='90'
        with self.assertRaisesRegex(ValueError,'OHLCV'):
            self.load(rows)

    def test_negative_volume_rejected(self):
        rows=sample()
        rows[100][5]='-1'
        with self.assertRaisesRegex(ValueError,'OHLCV'):
            self.load(rows)

if __name__=='__main__':
    unittest.main()
