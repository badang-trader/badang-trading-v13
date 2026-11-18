import unittest
from badang_reversal_multiframe_alignment import completed_higher_index,alignment,ema_at_closed_index
from badang_historical_integrity import FRAME_MS

def bars(frame,n=220):
    step=FRAME_MS[frame]
    return [[i*step,100+i*.1,101+i*.1,99+i*.1,100+i*.1,1] for i in range(n)]

class MultiFrameAlignmentTests(unittest.TestCase):
    def test_higher_forming_candle_excluded(self):
        higher=bars('30m')
        # 15m signal closes 00:15; 30m candle at 00:00 not closed.
        self.assertEqual(completed_higher_index(higher,'30m',900000),-1)
        self.assertEqual(completed_higher_index(higher,'30m',1800000),0)
    def test_future_higher_close_cannot_change_prior_alignment(self):
        lower=bars('15m',440);higher=bars('30m')
        histories={('BTC','15m'):lower,('BTC','30m'):higher}
        a=alignment(histories,'BTC','15m',430,'LONG')
        changed=[list(x) for x in higher]
        for x in changed[216:]:x[4]=99999
        b=alignment({('BTC','15m'):lower,('BTC','30m'):changed},'BTC','15m',430,'LONG')
        self.assertEqual(a,b)
        self.assertLessEqual(a['higher_last_close_ms'],lower[430][0]+FRAME_MS['15m'])
    def test_ema_history_requirement(self):
        self.assertIsNone(ema_at_closed_index(bars('15m',20),19,50))
        self.assertIsNotNone(ema_at_closed_index(bars('15m',20),19,20))

if __name__=='__main__':unittest.main()
