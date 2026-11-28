# 4.63 — Read-only worker interruption and restart evidence

- Added `badang_trade_recovery_463.py` and `/api/trade-recovery-463`.
- Bounded PostgreSQL history query detects earlier unfinished worker runs followed by a later run, while explicitly refusing to claim verified restart cause, backfill, continuous CVD or complete fills.
- Audit chronology and invalid timestamps are rejected. No orders or trading-score changes.
- New tests cover interruption, stale/failed runs, invalid history, no CVD promotion and bounded SQL query.
- No live PostgreSQL, Render restart or Bitget integration test was performed.
