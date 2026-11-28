import unittest
from badang_source_gate_440 import same_venue_derivatives

class SourceGateTests(unittest.TestCase):
    def test_cross_exchange_never_leaks(self):
        x = same_venue_derivatives('bitget', {'source_exchange':'okx','funding_rate':.01,'oi_contracts':100,'oi_change_1h_pct':3})
        self.assertEqual(x['status'],'CROSS_EXCHANGE_EXCLUDED')
        self.assertIsNone(x['funding_rate'])
        self.assertIsNone(x['oi_contracts'])
        self.assertIsNone(x['oi_change_1h_pct'])
    def test_same_exchange_kept(self):
        x = same_venue_derivatives('bitget', {'source_exchange':'BITGET','funding_rate':0.0,'oi_contracts':100})
        self.assertTrue(x['same_exchange'])
        self.assertEqual(x['funding_rate'],0.0)
        self.assertEqual(x['oi_contracts'],100)
    def test_missing_source_fails_closed(self):
        self.assertFalse(same_venue_derivatives('bitget', {})['same_exchange'])
    def test_invalid_payload_fails_closed(self):
        self.assertIsNone(same_venue_derivatives('bitget', None)['funding_rate'])

if __name__ == '__main__': unittest.main()
