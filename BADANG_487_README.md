# BADANG Trading 4.87 — worker audit/log safety

- The periodic worker rejects inconsistent `all_ok` flags before persisting audit success.
- Unsupported CVD, coverage, and order-readiness claims fail closed.
- Worker JSON logs allowlist `symbol` and `ok` instead of echoing arbitrary collector fields, reducing credential leakage risk.
- This is an audit-only REST snapshot collector, **not** continuous fills or verified CVD.
- Unit tests do not establish live Bitget, PostgreSQL, or Render readiness. Do not enable automated orders based on these checks.
