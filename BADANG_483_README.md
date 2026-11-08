# BADANG Trading 4.83 — worker/snapshot cross-check

Run after configuration and database schema preflight succeeds:

    python badang_worker_crosscheck_483.py

The check reads the worker-run history and the two newest snapshot timestamps for each configured symbol. It never writes database rows or sends orders. `RECENT_SAMPLES_AND_WORKER_ONLY` means only that the latest worker run and two recent timestamped snapshots meet limited criteria. It does NOT certify continuous exchange fills, gap-free CVD, or safe live trading.

The code has been tested using simulated DB-API connections. Live Render, PostgreSQL and Bitget integration has not been verified. Do not deploy this as an automated trading readiness gate.
