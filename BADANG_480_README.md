# BADANG Trading 4.80 — Read-only collection smoke check

Run `python badang_operational_smoke_480.py` in a reviewed deployment that includes this code and a configured PostgreSQL connection. It first runs the 4.79 database preflight, then queries the newest `fetched_ms` from `public.badang_trade_snapshots`. Default freshness window: 300000 ms (5 minutes). It does not create tables, write records, contact Bitget, or place orders.

A `RECENT_SAMPLE_ONLY` result proves only that a recent timestamp exists in the sampled-fill table. It does **not** verify fill completeness, CVD, continuity, signal quality, exchange connectivity, or safe trading. No live PostgreSQL/Render/Bitget access was used in development. Keep automated orders disabled until separate end-to-end verification.

Tests: `python -m unittest -v test_operational_smoke_480.py`.
