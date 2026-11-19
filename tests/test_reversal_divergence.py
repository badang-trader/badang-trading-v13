import unittest
from badang_reversal_divergence import confirmed_divergences

class DivergenceResearchTests(unittest.TestCase):
    def test_insufficient_bars(self):
        self.assertEqual(confirmed_divergences([]),[])
    def test_causal_timestamp(self):
        closes=[100+i*.1 for i in range(60)]
        rows=[(i*900000,c,c+1,c-1,c,1) for i,c in enumerate(closes)]
        for item in confirmed_divergences(rows):
            self.assertGreater(item['available_at_bar'],item['second_pivot_bar'])
            self.assertEqual(item['available_at_timestamp_ms'],rows[item['available_at_bar']][0])
    def test_no_future_pivot_detection(self):
        closes=[100+i*.1 for i in range(60)]
        rows=[(i*900000,c,c+1,c-1,c,1) for i,c in enumerate(closes)]
        self.assertEqual(confirmed_divergences(rows),[])

if __name__=='__main__':unittest.main()
