# BADANG Trading 5.12 — CI test evidence

- GitHub Actions offline-tests workflow runs the full read-only unittest audit and uploads `badang-ci-audit.json` as an artifact even when tests fail.
- Report contains only test counts, status, and recognized dependency names; no credentials, exception traces, market orders, or DB writes.
- Locally run `python badang_test_audit_508.py --report badang-ci-audit.json` from project root. The report path must be new (not an existing file or symlink).
- CI artifact `badang-offline-test-audit` is retained for 14 days.
- A green GitHub workflow is still **not** proof of Render/Bitget/PostgreSQL live readiness, market coverage, or trading safety.
- Local validation: 12 targeted tests passed; full suite ran 424 tests with 1 Flask import error (dependency blocked); syntax checked.
- GitHub/Render were not modified; no order execution enabled.
