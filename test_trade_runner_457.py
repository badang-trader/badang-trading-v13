import json
import threading
import unittest
from badang_trade_runner_457 import interval_from_env, run_periodic


class RunnerTests(unittest.TestCase):
    def test_interval_bounds(self):
        self.assertEqual(interval_from_env('60'), 60)
        for value in ('0', '14', '3601', 'nan', 'inf', '15.5', 'oops'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                interval_from_env(value)

    def test_multiple_cycles_do_not_overlap(self):
        events = []
        times = iter([0, 0, 0, 1, 1, 16, 16, 17, 17])
        def clock(): return next(times)
        def wait(seconds):
            events.append(('wait', seconds))
            return False
        def run():
            events.append(('run',))
            return {'all_ok': True, 'results': []}
        emitted = []
        self.assertEqual(run_periodic(run, 15, clock=clock, wait=wait,
                                      max_cycles=2, emit=emitted.append), 2)
        self.assertEqual([e for e in events if e[0] == 'run'], [('run',), ('run',)])
        self.assertEqual(len(emitted), 2)
        self.assertFalse(json.loads(emitted[0])['is_cvd'])

    def test_stop_before_first_cycle(self):
        stop = threading.Event()
        stop.set()
        self.assertEqual(run_periodic(lambda: self.fail('ran'), 15, stop=stop), 0)

    def test_exception_does_not_expose_message(self):
        emitted = []
        def fail(): raise RuntimeError('secret DATABASE_URL')
        run_periodic(fail, 15, max_cycles=1, emit=emitted.append)
        self.assertEqual(json.loads(emitted[0])['error_type'], 'RuntimeError')
        self.assertNotIn('secret', emitted[0])

    def test_invalid_cycles(self):
        with self.assertRaises(ValueError):
            run_periodic(interval=15, max_cycles=-1)

    def test_zero_cycles(self):
        self.assertEqual(run_periodic(lambda: self.fail('ran'), 15, max_cycles=0), 0)


if __name__ == '__main__':
    unittest.main()
