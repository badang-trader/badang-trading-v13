# BADANG Trading 4.48 — OI history integrity

Changes:
- Ignore corrupt (zero/non-finite) historical OI baselines when computing percentage changes.
- Reject a future-dated newest observation instead of reporting it as current.
- Add 5 database-mocked regression tests for full, stale, future, corrupt and missing histories.

Verification in this environment:
- `python -m pytest -q --ignore=test_oi_api_442.py`: 60 passed, 80 subtests passed.
- `python -m compileall -q .`: passed.
- `test_oi_api_442.py` could not run: Flask is not installed and package network access is unavailable.
- No live Bitget, PostgreSQL, or Render deployment verification.

NOT A PRODUCTION RELEASE. Do not replace the currently running deployment without full integration testing.
