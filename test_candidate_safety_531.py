"""Candidate ranking must never publish malformed scores or trade levels."""
import unittest
from app import recommend_candidates

def item(score=90,entry=100,stop=95,tp1=110):
    return {"signal":"LONG","long_score":score,"plan":{"entry":entry,"stop":stop,"tp1":tp1}}

class CandidateSafetyTests(unittest.TestCase):
    def test_valid_candidate(self):
        self.assertEqual(len(recommend_candidates([item()])),1)
    def test_nonfinite_and_nonpositive_levels(self):
        for value in (float("nan"),float("inf"),float("-inf"),0,-1,"bad"):
            with self.subTest(value=str(value)):
                self.assertEqual(recommend_candidates([item(entry=value)]),[])
                self.assertEqual(recommend_candidates([item(stop=value)]),[])
                self.assertEqual(recommend_candidates([item(tp1=value)]),[])
    def test_bad_scores(self):
        for value in (float("nan"),float("inf"),"oops",None,101,-1):
            with self.subTest(value=str(value)):
                self.assertEqual(recommend_candidates([item(score=value)]),[])
    def test_non_dict_item_and_thresholds(self):
        self.assertEqual(recommend_candidates([None,item()]),recommend_candidates([item()]))
        self.assertEqual(recommend_candidates([item()],min_rr=float("nan")),[])
        self.assertEqual(recommend_candidates([item()],min_score="oops"),[])
    def test_wrong_direction_geometry(self):
        self.assertEqual(recommend_candidates([item(stop=105)]),[])
        self.assertEqual(recommend_candidates([item(tp1=90)]),[])

if __name__=="__main__":unittest.main()
