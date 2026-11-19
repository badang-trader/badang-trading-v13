"""Elliott evidence must use only pivots confirmed by 3 right-side closed bars."""
import unittest
from app import wave_confluence_review

class ConfirmedWavePivotTests(unittest.TestCase):
    def setUp(self):
        self.rows=[[str(i*900000),'100','105','95','100','10'] for i in range(30)]
        self.points=[{'bar_index':i,'price':p} for i,p in zip((2,5,8,11,14,17),(100,110,105,120,113,125))]
    def test_confirmed_pivots_allowed(self):
        result=wave_confluence_review({'pivot_points':self.points},self.rows)
        self.assertEqual(result['status'],'AVAILABLE')
    def test_latest_pivot_requires_three_following_closed_bars(self):
        points=self.points[:-1]+[{'bar_index':27,'price':125}]
        result=wave_confluence_review({'pivot_points':points},self.rows)
        self.assertEqual(result['status'],'UNAVAILABLE')
        self.assertTrue(any('미확정' in w for w in result['warnings']))
    def test_negative_index_rejected(self):
        points=[dict(p) for p in self.points]
        points[0]['bar_index']=-1
        result=wave_confluence_review({'pivot_points':points},self.rows)
        self.assertEqual(result['status'],'UNAVAILABLE')
    def test_future_pivot_rejected(self):
        points=self.points[:-1]+[{'bar_index':30,'price':125}]
        result=wave_confluence_review({'pivot_points':points},self.rows)
        self.assertEqual(result['status'],'UNAVAILABLE')

if __name__=='__main__': unittest.main()
