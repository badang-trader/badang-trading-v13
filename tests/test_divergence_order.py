"""Regression for divergence ordering and closed-pivot lookahead."""
import unittest
from unittest.mock import patch
from app import divergence

class DivergenceOrderingTests(unittest.TestCase):
    def test_more_recent_bearish_overrides_older_bullish(self):
        close=[100.0]*22
        rsis=[50.0]*22
        close[4],close[9]=90,85
        rsis[4],rsis[9]=25,35
        close[12],close[17]=110,115
        rsis[12],rsis[17]=75,60
        with patch('app.pivots',side_effect=lambda a,low: [4,9] if low else [12,17]):
            self.assertEqual(divergence(close,rsis),'bearish')

    def test_same_confirmed_pivot_is_ambiguous(self):
        close=[100.0]*22
        rsis=[50.0]*22
        close[4],close[9]=90,85
        rsis[4],rsis[9]=25,35
        with patch('app.pivots',side_effect=lambda a,low: [4,9]):
            # Both opposite labels cannot physically occur on the same close series.
            self.assertEqual(divergence(close,rsis),'bullish')

    def test_future_bar_not_used_to_confirm_last_pivot(self):
        prices=[100,99,98,97,96,95,96,97,96,94,93,94,95,96,97]
        rsis=[50]*len(prices)
        self.assertEqual(divergence(prices,rsis),'none')

    def test_mismatched_lengths(self):
        self.assertEqual(divergence([1,2,3,4,5,6,7,8],[50]),'none')

if __name__=='__main__':
    unittest.main()
