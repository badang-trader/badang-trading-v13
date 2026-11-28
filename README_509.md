# BADANG Trading 5.09 — test audit mixed-failure guard

The audit now reports DEPENDENCY_BLOCKED **only** when all errors are recognized missing dependencies, with no assertion failures or skipped tests. Mixed failures are TESTS_FAILED_OR_SKIPPED; known missing dependency names remain visible without traceback contents.

Run: `python badang_test_audit_508.py`

No deployment, DB access, exchange requests, or trading is performed by this change. Full test suite still requires Flask; offline dependency installation failed because network DNS was unavailable.
