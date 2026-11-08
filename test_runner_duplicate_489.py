"""Duplicate symbol reports must not be logged or persisted as successful cycles."""
import json
import unittest
from badang_trade_runner_457 import run_periodic

class DuplicateResultTests(unittest.TestCase):
    def cycle(self, results):
        events=[]
        run_periodic(run=lambda:{'all_ok':True,'results':results}, interval=15,
                     max_cycles=1, emit=lambda msg:events.append(json.loads(msg)),
                     audit_start=lambda:'id', audit_finish=lambda rid,ok:events.append(('audit',ok)))
        return events

    def test_duplicate_success_fails_closed(self):
        events=self.cycle([{'symbol':'BTCUSDT','ok':True},{'symbol':'BTCUSDT','ok':True}])
        self.assertEqual(events[0],('audit',False))
        self.assertEqual(events[1]['failure_phase'],'collection')
        self.assertFalse(events[1]['all_ok'])

    def test_unique_symbols_remain_valid(self):
        events=self.cycle([{'symbol':'BTCUSDT','ok':True},{'symbol':'ETHUSDT','ok':True}])
        self.assertEqual(events[0],('audit',True))
        self.assertTrue(events[1]['all_ok'])

    def test_duplicate_secret_fields_not_emitted(self):
        events=self.cycle([{'symbol':'BTCUSDT','ok':True,'api_key':'SECRET'}, {'symbol':'BTCUSDT','ok':True}])
        self.assertNotIn('SECRET',json.dumps(events))

if __name__=='__main__': unittest.main()
