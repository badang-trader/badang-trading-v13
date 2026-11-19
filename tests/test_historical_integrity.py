import unittest
from badang_historical_integrity import audit_historical_candles

STEP=900000
def rows(n=4):
    return [[i*STEP,100,110,90,100,12] for i in range(n)]
class HistoricalIntegrityTests(unittest.TestCase):
    def test_valid_closed_contiguous(self):
        r=audit_historical_candles(rows(),'15m',asof_ms=4*STEP)
        self.assertEqual(r['bars'],4)
    def test_forming_bar_rejected(self):
        with self.assertRaisesRegex(ValueError,'forming'):
            audit_historical_candles(rows(),'15m',asof_ms=3*STEP+1)
    def test_gap_rejected(self):
        x=rows();x[2][0]+=STEP
        with self.assertRaises(ValueError):
            audit_historical_candles(x,'15m',asof_ms=5*STEP)
    def test_duplicate_rejected(self):
        x=rows();x[2][0]=x[1][0]
        with self.assertRaises(ValueError):
            audit_historical_candles(x,'15m',asof_ms=4*STEP)
    def test_negative_volume_rejected(self):
        x=rows();x[1][5]=-1
        with self.assertRaises(ValueError):
            audit_historical_candles(x,'15m',asof_ms=4*STEP)
    def test_unaligned_timestamp_rejected(self):
        x=rows();x[1][0]+=1
        with self.assertRaises(ValueError):
            audit_historical_candles(x,'15m',asof_ms=4*STEP)
if __name__=='__main__':unittest.main()
