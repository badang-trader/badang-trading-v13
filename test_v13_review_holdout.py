"""Exercise the scanner's real entry rules through the offline replay."""
import unittest

from badang_historical_integrity import FRAME_MS
from badang_v13_technical_holdout import audit_signals_on_15m, collect_signals, trade_ledger
from badang_walkforward_audit import audit_trades


class V13ReviewReplayTests(unittest.TestCase):
    as_of = 1795615200000

    def history(self):
        history = {}
        for tf in ('15m', '30m', '1H'):
            step = FRAME_MS[tf]
            rows = []
            for i in range(350):
                close = 100 + i * .01
                rows.append([self.as_of - (350 - i) * step, close - .015,
                             close + .10, close - .10, close, 10.])
            history['BTC', tf] = rows
        last = history['BTC', '15m'][-1]
        last[2], last[4], last[5] = 103.90, 103.75, 30
        return history

    def run_signals(self, history):
        return collect_signals(history, 'BTC', 'scalp', self.as_of - 2 * FRAME_MS['15m'])

    def test_uses_review_plan_and_cannot_see_later_higher_frame(self):
        history = self.history()
        technical, ready, counts = self.run_signals(history)
        self.assertEqual(counts['final_review_signals'], 1)
        self.assertEqual(technical[0]['score'], ready[0]['score'])
        self.assertNotEqual(technical[0]['target'], ready[0]['target'])

        # This extreme candle opens at the signal's close and is not observable.
        history['BTC', '1H'].append([self.as_of, 103, 105, 30, 31, 500.])
        self.assertEqual(self.run_signals(history), (technical, ready, counts))

    def test_technical_candidate_can_fail_final_review_on_higher_trend(self):
        history = self.history()
        for row in history['BTC', '1H']:
            row[1:5] = [204 - row[1], 204 - row[3], 204 - row[2], 204 - row[4]]
        technical, ready, counts = self.run_signals(history)
        self.assertEqual(len(technical), 1)
        self.assertEqual(counts['price_action_signals'], 1)
        self.assertEqual(counts['entry_checks_passed'], 0)
        self.assertEqual(ready, [])

    def test_ledger_keeps_position_identity_when_an_open_mark_becomes_a_stop(self):
        step = FRAME_MS['15m']
        candles = [[i * step, 100., 101., 99., 100.] for i in range(4)]
        candles[-1] = [3 * step, 95., 96., 94., 95.]
        signal = dict(bar=0, known_at_bar=0, signal_timestamp=0, mode='scalp',
                      side='LONG', score=90, stop=98., target=104.)

        def position(rows):
            trades = audit_trades(rows, [signal])['trades']
            return trade_ledger([dict(t, symbol='BTC', timeframe='15m', signal_timeframe='15m') for t in trades])[0]

        marked, closed = position(candles[:3]), position(candles)
        for key in ('symbol', 'mode', 'side', 'entry_ms', 'signal_close_ms'):
            self.assertEqual(marked[key], closed[key])
        self.assertEqual(marked['status'], 'OPEN')
        self.assertIsNone(marked['exit_price'])
        self.assertIsNone(marked['realized_net_return'])
        self.assertEqual(marked['mark_close_ms'], 3 * step)
        self.assertEqual(closed['status'], 'CLOSED')
        self.assertEqual(closed['exit_reason'], 'STOP')
        self.assertEqual(closed['exit_confirmed_close_ms'], 4 * step)
        self.assertEqual(closed['exit_price'], 95.)
        self.assertIsNone(closed['mark_price'])
        self.assertLess(closed['realized_net_return'], -.05)

    def test_swing_executes_only_after_hour_close_and_resolves_later_stop(self):
        step = FRAME_MS['15m']
        rows = [[i * step, 100., 101., 99., 100.] for i in range(7)]
        rows[2] = [2 * step, 100., 120., 80., 100.]
        rows[4] = [4 * step, 100., 106., 99., 104.]
        rows[5] = [5 * step, 100., 101., 94., 96.]
        signal = dict(signal_timestamp=0, mode='swing', side='LONG', score=90,
                      stop=98., target=104.)
        trades, missing = audit_signals_on_15m(rows, [signal], '1H')
        self.assertEqual(missing, 0)
        position, = trade_ledger([dict(t, symbol='BTC') for t in trades])
        self.assertEqual(position['entry_ms'], 4 * step)
        self.assertEqual(position['signal_close_ms'], 4 * step)
        self.assertEqual(position['exit_reason'], 'TARGET')
        self.assertEqual(position['exit_confirmed_close_ms'], 5 * step)
        self.assertEqual(position['signal_timeframe'], '1H')
        self.assertEqual(position['execution_timeframe'], '15m')

        trades, missing = audit_signals_on_15m(rows[4:], [signal], '1H')
        self.assertEqual(trades, [])
        self.assertEqual(missing, 1)


if __name__ == '__main__':
    unittest.main()
