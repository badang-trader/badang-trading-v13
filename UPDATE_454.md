# 4.54 PostgreSQL trade snapshot persistence (audit only)

- Added `badang_trade_postgres_454.py` with transaction-scoped per-symbol advisory locking, monotonic timestamp enforcement, JSONB snapshots, and collection gap diagnostics.
- Added 5 isolated mocked-DB tests in `test_trade_postgres_454.py`.
- This does **not** activate a collector, create continuous CVD, prove trade completeness, or affect trading scores.
- Requires configured `DATABASE_URL`, existing PostgreSQL privileges, and a separately deployed collection job. No production PostgreSQL, Bitget, or Render connectivity tested.
- Do not deploy without integration testing and verifying the source data schema.
