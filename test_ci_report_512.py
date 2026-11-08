"""Regression tests for offline audit evidence export."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import badang_test_audit_508 as audit_module


class CIReportTests(unittest.TestCase):
    def test_success_report(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'audit.json'
            with patch.object(audit_module, 'audit', return_value={'status': 'ALL_TESTS_PASSED', 'tests_run': 3}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = audit_module.main(['--report', str(report)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(report.read_text())['tests_run'], 3)

    def test_failure_still_writes_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'audit.json'
            with patch.object(audit_module, 'audit', return_value={'status': 'DEPENDENCY_BLOCKED'}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = audit_module.main(['--report', str(report)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(report.read_text())['status'], 'DEPENDENCY_BLOCKED')

    def test_existing_report_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'audit.json'
            report.write_text('existing')
            with patch.object(audit_module, 'audit', return_value={'status': 'ALL_TESTS_PASSED'}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = audit_module.main(['--report', str(report)])
            self.assertEqual(code, 2)
            self.assertEqual(report.read_text(), 'existing')

    def test_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'target'
            target.write_text('secret')
            link = Path(folder) / 'report.json'
            link.symlink_to(target)
            with patch.object(audit_module, 'audit', return_value={'status': 'ALL_TESTS_PASSED'}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = audit_module.main(['--report', str(link)])
            self.assertEqual(code, 2)
            self.assertEqual(target.read_text(), 'secret')

    def test_workflow_evidence_upload(self):
        workflow = Path(__file__).parent / '.github/workflows/offline-tests.yml'
        content = workflow.read_text()
        self.assertIn('badang_test_audit_508.py --report badang-ci-audit.json', content)
        self.assertIn('if: always()', content)
        self.assertIn('actions/upload-artifact@v4', content)
        self.assertNotIn('run: render', content.lower())

if __name__ == '__main__':
    unittest.main()
