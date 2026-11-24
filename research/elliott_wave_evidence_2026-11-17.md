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


## Follow-up evidence review — 2026-11-20 (research only)

### Source provenance and disagreement
- R.N. Elliott's *The Wave Principle* (1938) is the historical origin. EWI's history dates publication to 1938-08-31: https://www.elliottwave.com/free/introduction-to-the-wave-principle/ . The original full text was not independently inspected in this review; do not describe modern detailed rules as verbatim Elliott quotations.
- Frost & Prechter's *Elliott Wave Principle* (first published 1978) is a later interpretive textbook, not the 1938 primary source: https://www.elliottwave.com/books/elliott-wave-principle/
- EWI's diagonal discussion distinguishes ending diagonals (typically 3-3-3-3-3 internals) from leading diagonals; it acknowledges ambiguous leading-diagonal internals, including 5-3-5-3-5 in some cases: https://www.elliottwave.com/waveopedia/elliott-wave-pattern-diagonals/
- StockCharts' introduction describes leading diagonals as 5-3-5-3-5; this is a **source-dependent convention**, not an agreed universal classifier: https://chartschool.stockcharts.com/table-of-contents/market-analysis/elliott-wave-analysis-articles/identifying-elliott-wave-patterns
- D'Angelo & Grimaldi (2017), EUR/USD 2009–2015, report favorable retrospective forecasting: https://doi.org/10.5539/ibr.v10n6p1 . This does not establish out-of-sample BTC/ETH trading profitability.
- Applied Sciences (2024) on multi-agent Elliott interpretation explicitly discusses subjective labeling and overfitting risk: https://www.mdpi.com/2076-3417/14/24/11897 . No reproduction or independent cryptocurrency validation was completed in this review.

### Pattern taxonomy for a future research-only classifier
| Pattern | Indicative internals | Rule versus heuristic | Status in current engine |
| --- | --- | --- | --- |
| Ordinary impulse | 5-3-5-3-5 | wave 2 origin, wave 3 not shortest, wave 4 non-overlap: structural rules | Six extrema only; lower-degree internals unverified |
| Ending diagonal (wave 5/C) | 3-3-3-3-3 | wave 1/4 overlap is allowed; wedge, volume, throw-over are contextual | No dedicated classifier |
| Leading diagonal (wave 1/A) | disputed 3-3-3-3-3 or 5-3-5-3-5 | preserve source-specific alternatives | No dedicated classifier |
| Zigzag | 5-3-5 | B cannot exceed A origin; ratios are guidelines | Generic ABC swings only |
| Flat | 3-3-5 | B usually retraces >=90% of A; verify lower-degree structure | No dedicated classifier |
| Triangle | 3-3-3-3-3 (A-B-C-D-E) | require five legs and converging/other permitted boundaries | No dedicated classifier |
| W-X-Y / W-X-Y-X-Z | corrective combinations | require independent component classification | No dedicated classifier |
| Extended wave 3 / truncated 5 | requires nested impulse evidence | extension ratios and divergence are not proof | No confirmed detection |

### Specific hypothesis: downward wave 3 extension vs wave 5 exhaustion
- **Primary hypothesis A:** current fall is the end of wave 5. Minimum evidence: completed lower-degree fifth wave, non-contradictory higher-degree count, and confirmation after the final pivot is observable. RSI/MACD divergence or decreasing volume can support, but cannot establish completion.
- **Alternative hypothesis B:** current fall is an extended wave 3, with a later wave 4 and wave 5 still possible. Do not call a bounce a reversal merely because an oscillator diverges.
- Maintain both hypotheses as `unconfirmed` until enough closed bars and confirmed nested pivots exist. Every observation must record when the last pivot **became knowable**, not merely its historical pivot timestamp.
- An actual pattern-specific invalidation requires explicit rules per count and the correct pattern subtype. The current `invalidation_price` is a **structural reference** and must not be used as an automatic stop or a verified invalidation threshold.
- After a rule is contradicted, retire that count, retain alternatives, and recompute from information available at that closed bar. Never automatically reverse position.

### Causal validation protocol before any trading claim
1. Archive immutable candle batches with exchange, instrument, market type, timeframe, UTC open/close, data source, and ingestion timestamps. Reject duplicates, gaps and unfinished candles; do not infer completeness from 1000 rows alone.
2. At time `t`, generate pivots and candidates using only candles closed by `t`. Radius-3 pivot at index `i` first becomes observable at `i+3`; account for pivot replacement/repainting on subsequent bars.
3. Pre-register label definitions and outcome horizons (e.g. 5/10/20 bars), deduplicate correlated observations, and compare wave candidate policy against EMA/RSI baselines and a no-wave benchmark.
4. Walk-forward train/calibration/test partitions by chronological time; embargo overlapping horizons; hold out independent later market periods and separately BTC versus ETH. Do not tune Fibonacci bands on test sets.
5. Report by trend/range and high/low volatility regime, including coverage, calibration, false-positive rates, costs (maker/taker fees, spread, slippage, funding where applicable), net expectancy and maximum drawdown. A candidate count is not a trade.
6. Treat data gaps, API 429 and short history as explicit `unverified`, not `pass`. Maintain `trading_ready=false` until independently demonstrated.

### Current code audit, 2026-11-20
- `badang_analysis_v13.py::wave_candidates` remains a preliminary six-pivot / three-swing heuristic, not a validated nested Elliott classifier.
- `badang_wave_choice_response_587.py` preserves alternative candidates and marks structural levels `invalidation_rule_verified=false`, avoiding a false claim of actionable invalidation.
- `badang_wave_causal_replay_588.py` replays prefixes of closed candles, but it has no out-of-sample forecast evaluation, execution simulation or calibrated accuracy.
- `badang_wave_live_research_589.py` counts repeated observations, not independent trades. The report output newline was corrected in the validation branch in this review.
- No new predictive accuracy, net profitability, or independent-sample statistics were computed during this review. No main/Render/order changes.

## Follow-up causal candidate audit — 2026-11-24

### New verified code-level observation
- The research-only `badang_wave_choice_response_587.py` previously invoked `wave_candidates(pivots(rows))` without `total_bars`. As a result, the candidate engine's `observable_in_snapshot` metadata was not computed as true in this path, even when pivots were confirmed. The selection output did not expose `first_observable_bar_index` to the downstream replay. This is a causal traceability gap, not evidence of historical profitability.
- The research path now supplies `total_bars=len(rows)`, excludes candidates explicitly marked `observable_in_snapshot=False`, and carries confirmation metadata. Legacy/mock candidates with no metadata remain labeled `pivot_timing_verified=False`, not falsely certified.
- Regression tests cover unconfirmed-pivot rejection and confirmed-pivot timing metadata. The GitHub Actions result for the new commits must be checked separately; a committed test is not a passing test.
- This does **not** establish true nested-wave detection, completed 5th waves, or independent market outcomes.

### Theory and source comparison
- EWI Waveopedia explains that diagonal overlap is a pattern-specific exception; ending diagonals commonly have 3-3-3-3-3 subdivisions, while leading diagonal subdivision conventions are unsettled: https://www.elliottwave.com/waveopedia/elliott-wave-pattern-diagonals/
- ELWAVE distinguishes diagonal type 1 (3-3-3-3-3) from type 2 (5-3-5-3-5): https://elwave.com/elwave/faq/principle/principle2.html . This differs from sources that insist all diagonals subdivide into threes. The implementation must store the selected rulebook/version, rather than merge incompatible conventions.
- Vantuch, Zelinka & Vasant (2018), *An algorithm for Elliott Waves pattern detection*, evaluates pattern detection under different settings; its abstract does not establish BTC/ETH out-of-sample net trading returns: https://doi.org/10.3233/IDT-170319
- Elliott's original 1938/1946 texts were not directly authenticated in this run. Later pattern-taxonomy claims should not be presented as quotations from Elliott.

### Next falsifiable experiment
1. Archive closed Bitget BTC/ETH candles with exact timestamp and instrument metadata; reject gaps and open bars.
2. At each `t`, preserve candidate `first_observable_bar_index <= t`; test whether a candidate changes on subsequent prefixes. Record first detection, disappearance, and replacement.
3. Pre-register alternative hypotheses: H1 downward 5-wave exhaustion versus H2 nested downward third-wave extension. Label both as `unconfirmed` without nested degree evidence; define fixed future 5/10/20-bar outcomes independently from wave labels.
4. Compare against no-wave and simple trend baselines, walk-forward split with horizon embargo, distinct market regimes, fees/spread/slippage/funding. Report sample size, false signals, calibration, and net performance only after actual computation.
5. Separate wave-count invalidation from risk-stop distance; no automatic order execution or forced reversal.
