import unittest
from badang_reversal_artifact_consistency import validate_reversal_artifact

class ArtifactConsistencyTests(unittest.TestCase):
    def test_reject_missing_markets(self):
        with self.assertRaises(ValueError):
            validate_reversal_artifact({'primary_exchange':'BITGET','cases':[]})
    def test_reject_other_exchange(self):
        with self.assertRaises(ValueError):
            validate_reversal_artifact({'primary_exchange':'OKX','cases':[]})

if __name__=='__main__':unittest.main()
