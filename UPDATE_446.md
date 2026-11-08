# BADANG Trading 4.46 — Bitget OI response validation

- Introduced strict OI parser shared by PostgreSQL and SQLite observers.
- Rejects missing, zero, negative, nonfinite and ambiguous multi-row OI responses rather than storing incorrect readings.
- The value is the exchange-provided open-interest size, not necessarily USD notional.
- Added parser and observer tests.
- No production Bitget, PostgreSQL or Render integration was tested. No changes to trade recommendations or order execution.
- Do not deploy until remaining existing suite failures and real integrations are checked.
