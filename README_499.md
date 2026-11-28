# BADANG Trading 4.99 — per-symbol storage verification

The read-only consistency check now queries up to `limit` recent snapshots **per symbol** using a PostgreSQL window function. A globally limited query could conceal a less active symbol. The check also fails closed with `MISSING_SYMBOLS` when any configured symbol has no returned rows. `SAMPLE_COUNTS_MATCH` means only that the bounded stored samples have matching counts; it is NOT evidence of complete trade coverage, CVD, or trading readiness.

Run: `python badang_storage_consistency_498.py` after deployment to an authorized environment with a configured read-only PostgreSQL connection. No Render/Bitget production connectivity was exercised in this review.
