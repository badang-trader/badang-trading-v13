# BADANG Trading 4.84 — worker/snapshot provenance alignment

Crosscheck now requires the newest fetched snapshot for every reported symbol to
fall between the latest successful worker run's start and finish timestamps.
Missing or malformed per-symbol provenance fails closed as a warning. This
reduces false-positive status when the worker succeeds but does not refresh
snapshots. It does **not** prove complete exchange trade coverage or CVD, and
never enables orders. This is a code-level check only; PostgreSQL/Bitget/Render
integration is not verified.

Tests: `python -m unittest test_worker_crosscheck_483 test_worker_alignment_484`
