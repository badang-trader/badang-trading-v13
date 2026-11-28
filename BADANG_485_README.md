# BADANG Trading 4.85 — expected symbol set validation

Worker/snapshot alignment now requires the exact configured symbol set, rather than
accepting any nonempty subset. This prevents a missing ETH snapshot from passing
when BTC alone is recent. Unexpected or duplicate symbols fail closed.

Tests: `python -m unittest test_worker_crosscheck_483 test_worker_alignment_484 test_worker_symbols_485`

Read-only diagnostics only. No Bitget/Render/PostgreSQL live integration was performed.
Complete fills, CVD, and order safety remain unverified.
