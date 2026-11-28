import unittest
from badang_bitget_reversal_audit import audit_market_payload

class BitgetPerMarketAsOfTests(unittest.TestCase):
    def test_market_collected_after_manifest_start(self):
        step=900000
        # The manifest can precede a new closed bar collected later.
        payload={'candles':[[step,100,101,99,100,1]],
                 'provenance':{'collection_timestamp_ms':2*step}}
        self.assertEqual(audit_market_payload(payload,'15m')['status'],
                         'VALID_CLOSED_CONTIGUOUS')
    def test_market_forming_candle_still_rejected(self):
        step=900000
        payload={'candles':[[step,100,101,99,100,1]],
                 'provenance':{'collection_timestamp_ms':2*step-1}}
        with self.assertRaisesRegex(ValueError,'forming or future'):
            audit_market_payload(payload,'15m')

if __name__=='__main__':unittest.main()
