# 4.76 Read-only database readiness gate

Run `python badang_readiness_476.py` in the Render worker environment with `DATABASE_URL` set.
Exit code 0 means only the database connection, expected table presence and column types passed the two read-only checks. Exit code 1 means at least one check failed. Output is sanitized JSON without URLs or raw exception strings. Neither outcome verifies Bitget fill completeness, continuous CVD, or trading readiness.

Do not paste `DATABASE_URL` into chat or logs. Do not wire this script to automatic order placement.
