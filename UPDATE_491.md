# BADANG Trading 4.91 — ASCII-only audit symbol identifiers

- Reject non-ASCII Unicode lookalike symbols in `safe_cycle_outcome` before recording worker audit success.
- Added four regression tests covering Unicode full-width symbols, non-ASCII digits, normal ASCII symbols, and failed audit recording.
- Tests: 300 passed, 1 error (`test_oi_api_442`: Flask unavailable in this environment).
- This does not verify real Bitget, Render, PostgreSQL, complete fills coverage, CVD, or order safety.
