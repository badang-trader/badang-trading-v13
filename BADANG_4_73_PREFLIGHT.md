# BADANG Trading 4.73 — PostgreSQL read-only preflight

Run `python badang_db_preflight_473.py` with `DATABASE_URL` configured in a trusted environment. The output is sanitized JSON. This check only uses `SELECT` and never creates tables, writes data, collects exchange trades, or places orders. It verifies connection and presence of three public tables, not table schema correctness or permissions for future writes. Do not paste `DATABASE_URL` into chat or logs.

`database_reachable=true` and `schema_ready=true` are necessary but not sufficient for live deployment. Bitget connectivity, data integrity, continuous CVD, PostgreSQL write lifecycle, Render worker operation, and live trading remain unverified. Do not use REST trade samples as complete CVD or live trading signals.
