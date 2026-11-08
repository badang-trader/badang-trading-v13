# 5.06 — Evidence-based read-only operational diagnostics

The one-command gate now requires explicit, bounded storage inspection evidence (`checked_rows >= 2`, no missing symbols, per-symbol limit) and worker-to-snapshot provenance alignment. A success string alone cannot pass the gate. No trading orders or writes are added. This remains **recent REST fill samples only**, not continuous CVD or live trading readiness.

Run: `python badang_live_readonly_gate_501.py` on the deployed Render shell after reviewing and deploying the code. Requires configured PostgreSQL. No live environment was accessed during this release.
