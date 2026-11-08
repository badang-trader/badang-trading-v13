# BADANG Trading 4.79 — Render operator verification

Do **not** deploy this review ZIP to production without separately reviewing changes. These commands must run in a Render shell **after** the reviewed code is present there. They do not deploy code.

1. Confirm `DATABASE_URL` and the worker's `BADANG_TRADE_POLL_SECONDS` / `BADANG_TRADE_SYMBOLS` are set in Render's environment settings. Do not paste secrets into chat or logs.
2. Run `python badang_render_verify_479.py` to validate configuration **without network calls**. A successful result is `CONFIGURATION_ONLY_PASSED`; it does **not** prove PostgreSQL connectivity.
3. Run `python badang_render_verify_479.py --database` to perform the existing **read-only** PostgreSQL preflight. A successful result is `DATABASE_PREFLIGHT_PASSED`. Failure exits nonzero. Do not run migrations automatically.
4. Record only the returned JSON status and process exit code; do not share database URLs, API keys, or environment dumps.
5. Separately verify the actual worker startup, transaction persistence, Bitget request reliability, duplicate and missing trade handling, recovery after restarts, and UI signal quality before considering any trading action.

Both success statuses leave `trading_ready=false`, `safe_to_enable_orders=false`, `continuous_cvd_verified=false`. REST recent-fill samples are not complete-market CVD. No averaging-down or order placement is introduced.
