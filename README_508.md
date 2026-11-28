# BADANG Trading 5.08 — honest offline test audit

Run `python badang_test_audit_508.py` in the project directory.

The script runs the complete unittest discovery suite and emits a sanitized JSON summary. A missing Flask package is reported as `DEPENDENCY_BLOCKED`, **not** a pass. The process exits nonzero unless all discovered tests pass and none are skipped. It does not call exchanges, place orders, or connect to PostgreSQL by itself (some existing tests may have their own behavior).

This does not establish Render/Bitget/PostgreSQL readiness. No live deployment was changed.
