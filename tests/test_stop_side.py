"""Invalid stop-side regression: do not turn wrong-side stop into a 2R target."""
import unittest
from unittest.mock import patch
from app import analyze

class ProtectiveStopTests(unittest.TestCase):
    def test_long_stop_above_entry_is_rejected(self):
        rows=[]
        for i in range(205):
            # Prior candles are high; latest closed candle gaps down.
            price=100.0 if i==204 else 115.0
            rows.append([str(i*900000),'115','120','110',str(price),'100'])
        def fake_ema(values,n):
            if n==20: return [130.0]*len(values)
            if n==50: return [120.0]*len(values)
            if n==200: return [110.0]*len(values)
            if n==12: return [10.0]*len(values)
            if n==26: return [0.0]*len(values)
            if n==9: return [0.0]*len(values)
            raise AssertionError(n)
        with patch('app.candles',return_value=rows),patch('app.ema',side_effect=fake_ema),patch('app.rsi',return_value=60.0),patch('app.divergence',return_value='none'):
            result=analyze('BTCUSDT','15m')
        self.assertEqual(result['direction'],'WAIT')
        self.assertIsNone(result['stop'])
        self.assertIsNone(result['target'])

if __name__=='__main__':
    unittest.main()
