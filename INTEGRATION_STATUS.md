# BADANG Trading source review build

Based on the uploaded GitHub ZIP, not deployed. Do not overwrite the live application without staging validation.

Changes: discard stale (>24 bars), breached and duplicate heuristic wave candidates; show up to 2 per timeframe and count exclusions; remove unfiltered wave candidate duplicate UI; filter support above price and resistance below price from aggregated report. No averaging-down controls added.

Not completed: full Elliott rule validation, durable complete-market CVD/OI streaming, scanner/deep score integration, historical performance verification, live Bitget API test, Render deployment test. The structural score is not a probability. No trading authorization.

Tests: run `python -m unittest test_final_release test_integration_437`. The repository's pre-existing `test_release_static.py` has two mismatched assertions (`TECHNICAL_CANDIDATE_NOT_EXECUTION_ORDER` and a 15m/30m/1h UI label); these are not resolved in this review build. JavaScript syntax can be checked from the embedded HTML script.
