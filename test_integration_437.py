import unittest
from badang_wave_434 import audit_candidates
class WaveFiltering(unittest.TestCase):
 def setUp(self):self.bars=[{'start_ms':i*60000,'close':110} for i in range(80)]
 def candidate(self,age=2,side='UP',offset=0):
  return {'pivot_prices':[100,120+offset,105,125+offset], 'direction':side,'label':'test','last_pivot_ms':(79-age)*60000}
 def test_recent(self):
  self.assertEqual(len(audit_candidates({'candidates':[self.candidate()]},self.bars,3)['ranked']),1)
 def test_stale(self):
  r=audit_candidates({'candidates':[self.candidate(age=30)]},self.bars,3)
  self.assertEqual(r['excluded']['stale'],1);self.assertFalse(r['ranked'])
 def test_breach(self):
  r=audit_candidates({'candidates':[self.candidate(side='DOWN')]},self.bars,3)
  self.assertEqual(r['excluded']['reference_breached'],1)
 def test_duplicates(self):
  c=self.candidate();r=audit_candidates({'candidates':[c,c]},self.bars,3)
  self.assertEqual(r['excluded']['duplicate'],1)
 def test_max_two(self):
  r=audit_candidates({'candidates':[self.candidate(offset=i) for i in range(4)]},self.bars,3)
  self.assertEqual(len(r['ranked']),2)
 def test_empty(self):self.assertEqual(audit_candidates({'candidates':[]},self.bars,3)['ranked'],[])
