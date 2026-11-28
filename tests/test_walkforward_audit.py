"""Deterministic reference cases, not a real-market performance claim."""
import unittest
from badang_walkforward_audit import audit_trades,score_band

class WalkforwardAuditTests(unittest.TestCase):
    def setUp(self):
        self.rows=[
            (1,100,101,99,100),
            (2,100,103,99,102),
            (3,102,111,101,109),
            (4,109,110,108,109)]
    def test_next_bar_open_and_fee(self):
        result=audit_trades(self.rows,[dict(bar=0,known_at_bar=0,signal_timestamp=1,side='LONG',score=82,stop=95,target=110,mode='scalp')],fee_rate=.001,slippage_rate=.001)
        trade=result['trades'][0]
        self.assertEqual(trade['entry_bar'],1)
        self.assertEqual(trade['exit_bar'],2)
        self.assertAlmostEqual(trade['net_return'],.096)
        self.assertEqual(result['groups'][0]['samples'],1)
    def test_trade_details_and_end_of_data_reason(self):
        s=dict(bar=0,known_at_bar=0,signal_timestamp=1,side='LONG',score=90,stop=95,target=120)
        t=audit_trades(self.rows,[s])['trades'][0]
        self.assertEqual(t['signal_timestamp'],1)
        self.assertEqual(t['entry_price'],100)
        self.assertEqual(t['stop_price'],95)
        self.assertEqual(t['target_price'],120)
        self.assertEqual(t['exit_reason'],'END_OF_DATA')
        self.assertEqual(t['exit_timestamp'],4)
        self.assertAlmostEqual(t['net_return'],.09-.0018)

    def test_stop_reason(self):
        rows=[(1,100,101,99,100),(2,100,115,90,100),(3,100,101,99,100)]
        s=dict(bar=0,known_at_bar=0,signal_timestamp=1,side='LONG',score=90,stop=95,target=110)
        self.assertEqual(audit_trades(rows,[s])['trades'][0]['exit_reason'],'STOP')

    def test_same_bar_stop_wins(self):
        rows=[(1,100,101,99,100),(2,100,115,90,100),(3,100,101,99,100)]
        r=audit_trades(rows,[dict(bar=0,known_at_bar=0,signal_timestamp=1,side='LONG',score=90,stop=95,target=110)])
        self.assertLess(r['trades'][0]['net_return'],0)
    def test_empty_signals_no_fake_statistics(self):
        r=audit_trades(self.rows,[])
        self.assertEqual(r['status'],'HISTORICAL_SIGNALS_REQUIRED')
        self.assertEqual(r['groups'],[])
    def test_score_bins(self):
        self.assertEqual([score_band(x) for x in (79,80,84.99,85,89.99,90)], [None,'80-84','80-84','85-89','85-89','90+'])
    def test_reject_duplicate_timestamp(self):
        with self.assertRaises(ValueError):
            audit_trades([self.rows[0],self.rows[0],self.rows[2]],[])
    def test_short_win(self):
        rows=[(1,100,101,99,100),(2,100,101,90,95),(3,95,96,90,91)]
        r=audit_trades(rows,[dict(bar=0,known_at_bar=0,signal_timestamp=1,side='SHORT',score=86,stop=105,target=92,mode='swing')],fee_rate=0,slippage_rate=0)
        self.assertAlmostEqual(r['trades'][0]['net_return'],.08)
    def test_unstamped_signal_is_not_backtested(self):
        r=audit_trades(self.rows,[dict(bar=0,side='LONG',score=90,stop=95,target=110)])
        self.assertEqual(r['status'],'NO_ELIGIBLE_HISTORICAL_SIGNALS')
        self.assertEqual(r['trades'],[])

    def test_future_timestamp_signal_is_rejected(self):
        r=audit_trades(self.rows,[dict(bar=0,known_at_bar=2,side='LONG',score=90,stop=95,target=110)])
        self.assertEqual(r['trades'],[])

    def test_missing_timestamp_is_not_proven_history(self):
        r=audit_trades(self.rows,[dict(bar=0,known_at_bar=0,side='LONG',score=90,stop=95,target=110)])
        self.assertEqual(r['status'],'NO_ELIGIBLE_HISTORICAL_SIGNALS')

    def test_mismatched_timestamp_rejected(self):
        r=audit_trades(self.rows,[dict(bar=0,known_at_bar=0,signal_timestamp=2,side='LONG',score=90,stop=95,target=110)])
        self.assertEqual(r['trades'],[])

    def test_no_signal_bar_close_execution(self):
        r=audit_trades(self.rows,[dict(bar=0,known_at_bar=0,signal_timestamp=1,side='LONG',score=80,stop=95,target=110)])
        self.assertEqual(r['trades'][0]['entry_bar'],1)

if __name__=='__main__': unittest.main()
