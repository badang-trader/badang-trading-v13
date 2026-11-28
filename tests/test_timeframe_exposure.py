import unittest
from badang_timeframe_exposure import exposure_diagnostic

class ExposureTests(unittest.TestCase):
    def test_overlapping_frames_not_a_portfolio_return(self):
        def case(frame,start,entry,exit):
            return {'symbol':'BTC','timeframe':frame,
                'integrity':{'start_ms':start},
                'reversal_backtest':{'early':{'trades':[{'entry_bar':entry,'exit_bar':exit,'side':'LONG'}]}}}
        cases=[case('15m',0,0,4),case('30m',0,1,3)]
        r=exposure_diagnostic(cases,'early')
        self.assertEqual(r['maximum_simultaneous_timeframe_positions'],2)
        self.assertEqual(r['same_symbol_cross_timeframe_overlap_pairs'],1)
        self.assertEqual(r['max_simultaneous_by_symbol']['BTC'],2)
        self.assertEqual(r['portfolio_return'],'NOT_COMPUTABLE_WITHOUT_SIZING_AND_EXECUTION')
    def test_touching_intervals_not_overlap(self):
        def case(frame,start):
            return {'symbol':'BTC','timeframe':frame,
                'integrity':{'start_ms':start},
                'reversal_backtest':{'early':{'trades':[{'entry_bar':0,'exit_bar':0,'side':'SHORT'}]}}}
        r=exposure_diagnostic([case('15m',0),case('30m',900000)],'early')
        self.assertEqual(r['same_symbol_cross_timeframe_overlap_pairs'],0)
    def test_reject_unknown_kind(self):
        with self.assertRaises(ValueError):exposure_diagnostic([],'orders')

if __name__=='__main__':unittest.main()
