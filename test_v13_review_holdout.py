"""Exercise the scanner's real entry rules through the offline replay."""
import unittest

from badang_historical_integrity import FRAME_MS
from badang_v13_technical_holdout import collect_signals


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


if __name__ == '__main__':
    unittest.main()
