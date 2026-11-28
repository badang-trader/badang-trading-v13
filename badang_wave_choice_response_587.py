"""Research-only Elliott scenario selection and response planning.

The user-supplied chart screenshots motivate explicit alternative scenarios and
invalidation; they do not validate predictive accuracy. No trade orders.
"""
import math
from badang_analysis_v13 import normalize, pivots, wave_candidates

def wave_choice_response(candles):
    rows = normalize(candles)
    if len(rows) != len(candles):
        return {"status": "invalid_data", "trading_ready": False, "scenarios": []}
    if len(rows) < 25:
        return {"status": "insufficient_data", "trading_ready": False, "scenarios": []}
    candidates = wave_candidates(pivots(rows))
    close = rows[-1]["close"]
    scenarios = []
    for candidate in candidates:
        invalidation = candidate.get("invalidation_price")
        if (not isinstance(invalidation, (int, float))
                or isinstance(invalidation, bool)
                or not math.isfinite(invalidation) or invalidation <= 0):
            continue
        direction = candidate.get("direction")
        if direction not in ("up", "down"):
            continue
        # Existing levels are structural reference pivots, not verified
        # directional invalidation or automatic stop-loss thresholds.
        scenarios.append({
            "pattern": candidate["pattern"],
            "direction": direction,
            "confidence": candidate.get("confidence", "low"),
            "invalidation_price": invalidation,
            "current_close": close,
            "invalidation_status": "not_evaluated",
            "level_semantics": "structural_reference_only",
            "invalidation_rule_verified": False,
            "response_if_invalidated": "recount_wave_and_reassess; do_not_auto_reverse",
            "response_if_supported": "await_independent_confirmation_before_entry",
            "source": "existing_elliott_wave_candidate_engine",
        })
    return {
        "status": "candidates" if scenarios else "no_valid_candidate",
        "selection_policy": "compare_alternatives; never_force_single_count",
        "trading_ready": False,
        "automatic_orders": False,
        "scenarios": scenarios,
    }
