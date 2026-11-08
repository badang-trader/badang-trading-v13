"""Validate CI safety contract using Python stdlib only."""
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parent / '.github/workflows/offline-tests.yml'

class CIWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = PATH.read_text(encoding='utf-8')

    def test_triggers(self):
        for expected in ('  push:', '  pull_request:', '  workflow_dispatch:'):
            self.assertIn(expected, self.body)

    def test_read_only_permissions(self):
        self.assertIn('permissions:\n  contents: read', self.body)

    def test_no_deploy_or_secret_usage(self):
        for banned in ('secrets.', 'render deploy', 'deploy-hook', 'docker push', 'actions/deploy'):
            self.assertNotIn(banned, self.body.lower())

    def test_install_then_audit(self):
        self.assertLess(self.body.index('python -m pip install -r requirements.txt'),
                        self.body.index('python badang_test_audit_508.py'))

    def test_required_integration_dependencies_checked_before_audit(self):
        self.assertIn("('flask', 'requests', 'psycopg2')", self.body)
        self.assertLess(self.body.index('Verify required integration dependencies'),
                        self.body.index('Run offline audit (must pass fully)'))

    def test_no_database_connection(self):
        self.assertIn("DATABASE_URL: ''", self.body)
        self.assertIn("BADANG_TRADING_ENABLED: 'false'", self.body)

if __name__ == '__main__': unittest.main()
