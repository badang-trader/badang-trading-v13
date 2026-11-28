# BADANG Trading 4.93 — offline worker acceptance gate

Added `test_offline_acceptance_493.py`, five end-to-end worker-path checks using injected collection and audit callbacks. It checks success, missing symbols, collection exception, ambiguous audit finish, and forged CVD readiness claims. The actual worker logic is exercised, but Bitget, PostgreSQL, Render, Flask and trading orders are **not** connected or verified.

Run: `python -m unittest -v test_offline_acceptance_493` from the project directory.

This package is a review candidate only, not a live-trading release. Do not activate automatic orders on the basis of offline tests.
