# 4.56 — bounded network retry for audit-only trade snapshots

- Added `badang_trade_job_456.py`: retries transient fetch failures only (up to three attempts with exponential backoff); preserves per-symbol failure isolation.
- Never retries database writes after ambiguous commit; does not assert complete coverage or CVD.
- Added `test_trade_job_456.py` with six focused tests.
- Run with `python badang_trade_job_456.py` from an external scheduler after configuring PostgreSQL. No schedule is deployed by this release.
- No live Bitget, PostgreSQL, or Render deployment verification performed. Do not treat this as production-ready continuous market data.
