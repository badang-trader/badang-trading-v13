import unittest
from badang_wave_divergence_association import associate_prior_divergences

class WaveDivergenceAssociationTests(unittest.TestCase):
    def test_only_strictly_earlier(self):
        scenarios=[{'scenario':'POSSIBLE_ABC_ZIGZAG_END','status':'UNVALIDATED_ABC_GEOMETRY','available_at_bar':50}]
        divergences=[
            {'classification':'REGULAR_BULLISH','indicator':'RSI','available_at_bar':25},
            {'classification':'REGULAR_BULLISH','indicator':'RSI','available_at_bar':26},
            {'classification':'HIDDEN_BULLISH','indicator':'MACD','available_at_bar':49},
            {'classification':'REGULAR_BEARISH','indicator':'RSI','available_at_bar':50},
            {'classification':'HIDDEN_BEARISH','indicator':'MACD','available_at_bar':51}]
        result=associate_prior_divergences(scenarios,divergences)[0]
        self.assertEqual(result['strictly_prior_divergences'],2)
        self.assertEqual(result['same_bar_unordered'],1)
        self.assertEqual(result['later_divergences_excluded'],1)
        self.assertEqual(result['prior_by_type_indicator']['HIDDEN_BULLISH_MACD'],1)
    def test_no_scenarios(self):
        self.assertEqual(associate_prior_divergences([],[]),[])
    def test_invalid_window(self):
        with self.assertRaises(ValueError):associate_prior_divergences([],[],lookback=0)

if __name__=='__main__':unittest.main()
