import unittest
from badang_signal_audit_439 import reconcile

class AuditTests(unittest.TestCase):
    def base(self):
        return dict(candidate_side='LONG',technical_side='LONG',exchange='bitget',
                    trend_aligned=True,data_quality={'cross_exchange':False},
                    signal_precision_418={'status':'CANDIDATE'},
                    futures_data_available={'oi_history':False},
                    cvd_quality='UNAVAILABLE_BITGET_UNVERIFIED')
    def test_good_direction_is_only_review(self):
        x=reconcile(self.base())
        self.assertEqual(x['status'],'REVIEW_ONLY')
        self.assertFalse(x['order_authorized'])
        self.assertIsNone(x['probability'])
        self.assertEqual(len(x['missing_flow']),2)
    def test_missing_precision_waits(self):
        d=self.base();d.pop('signal_precision_418')
        self.assertEqual(reconcile(d)['status'],'WAIT')
    def test_cross_exchange_waits(self):
        d=self.base();d['data_quality']['cross_exchange']=True
        self.assertEqual(reconcile(d)['status'],'WAIT')
    def test_conflict_waits(self):
        d=self.base();d['technical_side']='SHORT'
        self.assertEqual(reconcile(d)['status'],'WAIT')
    def test_no_direction_waits(self):
        d=self.base();d['candidate_side']='WAIT'
        self.assertEqual(reconcile(d)['status'],'WAIT')
    def test_flow_missing_does_not_invent_negative_signal(self):
        d=self.base();d['futures_data_available']['oi_history']=True
        self.assertEqual(reconcile(d)['status'],'REVIEW_ONLY')
        self.assertEqual(len(reconcile(d)['missing_flow']),1)
if __name__=='__main__':unittest.main()
