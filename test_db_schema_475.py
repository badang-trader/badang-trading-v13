import unittest
from badang_db_schema_474 import REQUIRED, inspect_schema
from test_db_schema_474 import Cursor, Connection

class MetadataRobustnessTests(unittest.TestCase):
    def rows(self):
        return [(table, col, dtype) for table, cols in REQUIRED.items() for col, dtype in cols.items()]
    def test_duplicate_metadata_fails_closed(self):
        rows=self.rows()
        result=inspect_schema(lambda:Connection(Cursor(rows+[rows[0]])))
        self.assertFalse(result['schema_compatible'])
        self.assertEqual(result['duplicate_metadata'][0]['column'],rows[0][1])
    def test_malformed_metadata_fails_closed(self):
        result=inspect_schema(lambda:Connection(Cursor([('badang_trade_snapshots', 'symbol')])))
        self.assertFalse(result['schema_compatible'])
        self.assertEqual(result['error_type'],'ValueError')
    def test_unexpected_table_does_not_mask_missing(self):
        result=inspect_schema(lambda:Connection(Cursor([('unrelated','symbol','text')])))
        self.assertFalse(result['schema_compatible'])
        self.assertIn('badang_trade_snapshots',result['mismatches'])
    def test_no_sensitive_metadata_in_errors(self):
        result=inspect_schema(lambda:Connection(Cursor([('secret_password',None,'text')])))
        self.assertNotIn('secret_password',str(result))
        self.assertFalse(result['schema_compatible'])

if __name__=='__main__': unittest.main()
