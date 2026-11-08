"""Research analyzer must never normalize impossible nonpositive OHLC."""
import unittest
from badang_analysis_v13 import normalize,analyze

def bar(o=100,h=102,l=99,c=101,v=10):
    return [0,o,h,l,c,v]

class NormalizeSafetyTests(unittest.TestCase):
    def test_reject_nonpositive_open_high_low_close(self):
        for index in (1,2,3,4):
            for bad in (0,-1):
                with self.subTest(index=index,bad=bad):
                    r=bar()
                    r[index]=bad
                    self.assertEqual(normalize([r]),[])
    def test_reject_nonfinite_or_overflow(self):
        for bad in (float("nan"),float("inf"),float("-inf"),10**10000):
            with self.subTest(value=str(type(bad))):
                r=bar()
                r[4]=bad
                self.assertEqual(normalize([r]),[])
    def test_invalid_bar_cannot_satisfy_minimum_history(self):
        rows=[bar() for _ in range(204)]+[bar(o=-1)]
        result=analyze(rows)
        self.assertEqual(result["status"],"insufficient_data")
        self.assertEqual(result["recommendation"],"WAIT")

if __name__=="__main__":unittest.main()
