# BADANG Trading 5.05 — REST sample safety-claim validation

## Changes
- In `badang_worker_crosscheck_483.py`, optional safety claims from snapshot-progress and per-symbol sample reports must be literal `False` if present. Strings, numbers, nulls and other non-boolean values cannot be interpreted as proof of safety.
- Added checks for `is_cvd` and `used_in_trading_score` alongside coverage, continuous CVD and order-readiness claims.
- Added `test_worker_claims_505.py` regression tests.

## Verified locally
- `python -m unittest -q test_worker_crosscheck_483 test_worker_claims_505`: 13 tests passed.
- `python -m unittest discover -q`: 379 tests run, one import error because Flask is unavailable in this execution environment; other 378 tests passed.
- No Render, Bitget or live PostgreSQL connection was tested. No trading orders are enabled.
