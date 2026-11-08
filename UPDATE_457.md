# 4.57 — Periodic audit snapshot runner

- Added `badang_trade_runner_457.py`: dedicated-process polling runner (default 60 seconds; configurable `BADANG_TRADE_POLL_SECONDS` 15–3600).
- Runs each collection cycle sequentially; handles SIGTERM/SIGINT; skips missed ticks rather than backfilling them.
- Emits metadata-only JSON cycle reports; no API secrets or payloads in logs.
- Added six tests in `test_trade_runner_457.py`.
- Launch as a separate worker with `python badang_trade_runner_457.py`, not inside Flask/Gunicorn. Configure DATABASE_URL and BADANG_TRADE_SYMBOLS. Do not run multiple worker replicas without coordination.
- **NOT** deployed to Render. No live PostgreSQL/Bitget verification. REST polling samples are not complete market coverage or continuous CVD; no trading score use.
