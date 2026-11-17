# Elliott wave research note — 2026-11-17 (read-only)

## Evidence hierarchy
- EWI Waveopedia impulse: https://www.elliottwave.com/waveopedia/impulse/
- EWI rules vs guidelines: https://www.elliottwave.com/articles/elevate-your-elliott-wave-analysis/
- EWI diagonals: https://www.elliottwave.com/waveopedia/elliott-wave-pattern-diagonals/
- EWI zigzags: https://www.elliottwave.com/waveopedia/zigzags/
- EWI combinations: https://www.elliottwave.com/waveopedia/combinations/
- Vantuch, Zelinka & Vasant (2018), *An algorithm for Elliott Waves pattern detection*: https://doi.org/10.3233/IDT-170319 (abstract accessible; results not independently reproduced)
- Ribeiro (2019), application to PSI20: https://doi.org/10.25115/eea.v37i2.2607 (case study, not evidence of BTC/ETH profitability)

## Key distinctions
1. Ordinary impulse (5-3-5-3-5): wave 2 cannot retrace beyond wave 1 origin; wave 3 cannot be shortest of waves 1/3/5; wave 4 cannot overlap wave 1 price territory. Confirmed subwave structures require lower-degree evidence, not merely six pivot endpoints.
2. Diagonals are **separate** motive patterns: wave 4/1 overlap is commonly permissible. Ending diagonal normally occurs at wave 5 or C, with 3-3-3-3-3 internals. Leading diagonal may have disputed 5-3-5-3-5 internals; preserve source-specific ambiguity rather than forcing a single classification.
3. Zigzag ABC is 5-3-5; a generic three-swing alternating pivot pattern with Fibonacci ratios is insufficient to label a confirmed zigzag. Flat 3-3-5, triangle 3-3-3-3-3, and W-X-Y combinations need separate classifiers.
4. Fibonacci ratios, alternation, momentum divergence, volume, and ending-diagonal reversal behavior are **guidelines / hypotheses**, not deterministic invalidation rules or validated trading signals.
5. Do not equate a structural pivot with a directional invalidation threshold or automatic stop-loss. The invalidation must be pattern-specific and independently tested.

## Existing engine gap (badang_analysis_v13.py / wave_candidates)
- Six pivot endpoints and swing lengths identify preliminary impulse candidates, but no 5-3-5-3-5 nested validation, no diagonal classifier, and no confirmed wave-degree attribution.
- The three-swing ABC candidate uses B/A and C/A ratios but does not validate the 5-3-5 subdivision.
- Pivot confirmation timing must be retained when replaying historical observations: a pivot identified using later candles cannot be credited to an earlier signal.
- A 'medium' confidence based on Fibonacci bands is a heuristic label, **not** calibrated probability.

## Prioritized implementation specification (NOT deployed)
A. Create a *research-only* candidate state machine: `unconfirmed`, `structurally_possible`, `structurally_invalid`, `subdivisions_verified`; retain multiple alternative counts.
B. For ordinary impulses, check wave-2 origin, wave-3 shortest condition (only after wave 5 exists), wave-4 overlap using high/low extremes where data are available; do not silently apply diagonal exceptions.
C. Record per-candidate `first_observable_bar`, pivot confirmation delay, degree, rule evidence, disqualifying observation, and separate **pattern invalidation** from **risk stop**.
D. Distinguish extension of wave 3 vs completion of wave 5 using alternative counts, lower-degree subdivisions and confirmation, not divergence alone.
E. Evaluate fixed forward horizons with fully closed candles, walk-forward holdouts, fees/slippage, regime stratification and baseline comparisons; deduplicate overlapping signals. Report precision, calibration, net expectancy and drawdown only when computed.
F. Never claim trading readiness until CI, causal replay, independent sample, and operational safety gates all pass.

## Current verification status
Existing GitHub Actions on commit `36cd56d1` (2026-11-15 UTC) show **807 tests, 2 failures**. The test audit suppresses failure traceback; root causes remain unverified. This research note is not a code fix or passing test claim. Do not merge into main or deploy to Render.
