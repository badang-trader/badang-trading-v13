# BADANG 4.38 — data quality gate

Based on the 4.37 review archive. The existing scanner is not replaced and deep analysis remains a separate diagnostic.

- Each deep timeframe is excluded from trend aggregation when explicitly unusable, missing >0 candle intervals, has fewer than 200 closed candles, lacks valid EMA/ATR, or is marked LIMITED.
- Coverage statuses: COMPLETE (4/4), PARTIAL (2–3/4), INSUFFICIENT (<2/4 or price mismatch >3%).
- With insufficient coverage, trend is deferred and aggregated support/resistance is suppressed.
- Data quality status is displayed in the deep-analysis section.
- No averaging-down / additional-entry settings were added.
- Existing Elliott fit scores remain heuristic, not probability or confirmed wave count.
- CVD/OI streaming, unified scanner score, live exchange verification, historical signal outcome tests, Render staging deployment: NOT completed.

Tests: `python -m unittest test_final_release test_integration_437 test_quality_438`.
Do not deploy to a live trading workflow without staging tests and review of the changes.
