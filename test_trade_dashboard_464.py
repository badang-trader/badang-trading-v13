import unittest
from pathlib import Path

class DashboardWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).with_name('app.py').read_text(encoding='utf-8')

    def test_status_slot(self):
        self.assertIn('id="recovery464status"', self.source)

    def test_fetch_read_only(self):
        self.assertIn("/api/trade-recovery-463", self.source)

    def test_refresh_wired_to_deep_analysis(self):
        self.assertIn('refreshWorker462();refreshRecovery464();', self.source)

    def test_no_cvd_promotion(self):
        self.assertIn('d.backfill_verified!==false||d.restart_cause_known!==false', self.source)
        self.assertIn('누락 복구 미검증 · CVD/점수 미반영', self.source)

    def test_bounded_history_warning(self):
        self.assertIn("d.history_limited===true", self.source)

if __name__ == '__main__': unittest.main()
