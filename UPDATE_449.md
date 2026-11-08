# 4.49 OI read-only UI integration

- Deep analysis now reads /api/oi-history-442 with GET for the selected symbol.
- 15m and 1h OI changes are displayed only when matching Bitget records exist.
- Missing, stale, cross-exchange, or invalid data is not inferred.
- Browser never POSTs OI observations or exposes the collector token.
- OI is not used in trading score; CVD remains unverified.
- Updated legacy Flask API tests to supply collector auth for POST and added 403 check.
- Not production deployed or live Bitget tested.
