# BADANG Trading 4.69 — transactional lifecycle simulation

Added `test_trade_lifecycle_469.py` with five integration-style scenarios connecting the periodic worker, audit start/finish operations, a transactional in-memory PostgreSQL stand-in, and the run-state assessment.

Scenarios: successful commit; collector exception recorded as failed; finish-write failure must not be reported as success; new cycle after an unfinished historical cycle does not establish recovery; duplicate finish rejected without changing the original record.

**Scope:** This is a simulated database, not a live PostgreSQL integration test. Bitget, Flask runtime, Render and real database connectivity are not validated. CVD completeness remains unverified and trading-score use remains disabled.
