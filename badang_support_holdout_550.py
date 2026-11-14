"""Chronological holdout evaluation for support-zone research.

This does NOT optimize parameters or produce trading signals. Training data is
not used to select the best horizon, threshold, or evidence cutoff here.
"""
from __future__ import annotations
import math
from badang_support_backtest_545 import support_touch_backtest
from badang_support_timestamp_gate_544 import FRAME_MS


def chronological_support_holdout(candles, symbol, timeframe, mode="scalp",
                                  *, exchange_now_ms, train_fraction=0.7,
                                  horizon=8, warmup=90, rebound_pct=0.5,
                                  min_resolved=30):
    if timeframe not in FRAME_MS:
        raise ValueError("unsupported timeframe")
    if (isinstance(train_fraction, bool) or
            not isinstance(train_fraction, (int, float)) or
            not math.isfinite(train_fraction) or
            not 0.5 <= train_fraction <= 0.85):
        raise ValueError("train_fraction must be 0.5 to 0.85")
    if isinstance(min_resolved, bool) or not isinstance(min_resolved, int) or min_resolved < 1:
        raise ValueError("min_resolved must be positive")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 48:
        raise ValueError("invalid horizon")
    if isinstance(warmup, bool) or not isinstance(warmup, int) or warmup < 60:
        raise ValueError("invalid warmup")
    if (isinstance(rebound_pct, bool) or
            not isinstance(rebound_pct, (int, float)) or
            not 0 < rebound_pct <= 20):
        raise ValueError("invalid rebound threshold")
    if not isinstance(candles, (list, tuple)) or len(candles) < warmup + horizon + 2:
        return {"status": "insufficient_history", "trading_ready": False}
    split = int(len(candles) * train_fraction)
    if split < warmup + horizon + 1 or len(candles) - split < horizon + 1:
        return {"status": "insufficient_split_history", "trading_ready": False}

    # Use complete history to form holdout support zones causally at each
    # holdout touch. The training portion is never replaced by a synthetic
    # warmup, and no future holdout bars are visible to earlier signals.
    result = support_touch_backtest(
        candles, symbol, timeframe, mode, exchange_now_ms=exchange_now_ms,
        horizon=horizon, warmup=warmup, rebound_pct=rebound_pct,
        max_events=1000)
    if result["status"] != "ok":
        return {"status": result["status"], "trading_ready": False}
    # A capped event scan can omit later holdout observations and bias the
    # comparison. Refuse to publish a partial holdout in that case.
    if result.get("event_cap_reached", len(result["events"]) >= 1000):
        return {"status": "event_cap_reached", "trading_ready": False,
                "warnings": ["Holdout omitted: capped scan may exclude later events"]}
    if not result.get("scan_complete", len(result["events"]) < 1000):
        return {"status": "incomplete_scan", "trading_ready": False,
                "warnings": ["Holdout omitted: full historical scan not confirmed"]}
    # Only include events whose full evaluation horizon lies within the
    # training or holdout segment. Discard the split-boundary overlap.
    train = [e for e in result["events"]
             if e["touch_bar_index"] + horizon < split]
    holdout = [e for e in result["events"]
               if e["touch_bar_index"] >= split
               and e["touch_bar_index"] + horizon < len(candles)]
    return {
        "status": "ok", "symbol": symbol, "timeframe": timeframe,
        "split_index": split, "train": _summary(train, min_resolved),
        "holdout": _summary(holdout, min_resolved),
        "holdout_sample_adequate": sum(
            e["outcome"] in ("rebound", "breakdown", "breakdown_on_touch")
            for e in holdout) >= min_resolved,
        "holdout_event_coverage": {
            "first_touch_index": min((e["touch_bar_index"] for e in holdout), default=None),
            "last_touch_index": max((e["touch_bar_index"] for e in holdout), default=None),
            "holdout_bars": len(candles) - split,
        },
        "parameters_predeclared": None,
        "parameter_selection_audited": False,
        "trading_ready": False,
        "warnings": [
            "Parameter selection history is not independently audited",
            "Holdout results are descriptive, not a guaranteed future success rate",
            "No fees, slippage, or liquidation simulation",
            "Minimum sample count is not statistical confidence calibration",
        ],
    }


def _summary(events, minimum):
    counts = {k: sum(e["outcome"] == k for e in events)
              for k in ("rebound", "breakdown", "breakdown_on_touch",
                        "ambiguous", "unresolved")}
    resolved = counts["rebound"] + counts["breakdown"] + counts["breakdown_on_touch"]
    rebound_mae = [e["pre_outcome_max_adverse_excursion_pct"]
                   for e in events if e["outcome"] == "rebound"]
    return {
        "event_count": len(events),
        "resolved_count": resolved,
        "counts": counts,
        "by_evidence_grade": {
            grade: _grade_summary(events, grade, minimum)
            for grade in ("strong_evidence", "moderate_evidence", "limited_evidence", "ungraded")
        },
        "by_pre_touch_regime": {
            regime: _regime_summary(events, regime, minimum)
            for regime in ("up", "down", "sideways", "unclassified")
        },
        "adequate_sample": resolved >= minimum,
        "rebound_fraction": (
            round(counts["rebound"] / resolved, 4) if resolved >= minimum else None),
        "mean_pre_rebound_mae_pct": (
            round(sum(rebound_mae) / len(rebound_mae), 4)
            if rebound_mae and resolved >= minimum else None),
    }


def _grade_summary(events, grade, minimum):
    selected = [e for e in events if (e.get("evidence_grade_at_touch") not in
                       ("strong_evidence", "moderate_evidence", "limited_evidence")
                       if grade == "ungraded" else e.get("evidence_grade_at_touch") == grade)]
    rebound = sum(e["outcome"] == "rebound" for e in selected)
    breakdown = sum(e["outcome"] in ("breakdown", "breakdown_on_touch") for e in selected)
    resolved = rebound + breakdown
    mae_by_outcome = {}
    for outcome in ("rebound", "breakdown", "breakdown_on_touch", "unresolved"):
        values = [e["pre_outcome_max_adverse_excursion_pct"] for e in selected
                  if e["outcome"] == outcome and
                  isinstance(e.get("pre_outcome_max_adverse_excursion_pct"), (int, float)) and
                  not isinstance(e["pre_outcome_max_adverse_excursion_pct"], bool) and
                  math.isfinite(e["pre_outcome_max_adverse_excursion_pct"]) and
                  e["pre_outcome_max_adverse_excursion_pct"] >= 0]
        mae_by_outcome[outcome] = {
            "count": len(values),
            "mean_pre_outcome_mae_pct": round(sum(values) / len(values), 4) if values else None,
            "max_pre_outcome_mae_pct": max(values) if values else None,
        }
    return {"events": len(selected), "resolved": resolved,
            "rebound": rebound, "breakdown": breakdown,
            "pre_outcome_mae_by_outcome": mae_by_outcome,
            "rebound_fraction": round(rebound / resolved, 4) if resolved >= minimum else None,
            "sample_adequate": resolved >= minimum}


def _regime_summary(events, regime, minimum):
    selected = [e for e in events if (
        e.get("regime_before_touch") not in ("up", "down", "sideways")
        if regime == "unclassified" else e.get("regime_before_touch") == regime)]
    rebound = sum(e["outcome"] == "rebound" for e in selected)
    breakdown = sum(e["outcome"] in ("breakdown", "breakdown_on_touch") for e in selected)
    resolved = rebound + breakdown
    return {"events": len(selected), "resolved": resolved,
            "rebound": rebound, "breakdown": breakdown,
            "rebound_fraction": round(rebound / resolved, 4) if resolved >= minimum else None,
            "sample_adequate": resolved >= minimum}
