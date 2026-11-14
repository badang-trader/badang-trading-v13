"""Chronological holdout evaluation for support-zone research.

This does NOT optimize parameters or produce trading signals. Training data is
not used to select the best horizon, threshold, or evidence cutoff here.
"""
from __future__ import annotations
from badang_support_backtest_545 import support_touch_backtest
from badang_support_timestamp_gate_544 import FRAME_MS


def chronological_support_holdout(candles, symbol, timeframe, mode="scalp",
                                  *, exchange_now_ms, train_fraction=0.7,
                                  horizon=8, warmup=90, rebound_pct=0.5,
                                  min_resolved=30):
    if timeframe not in FRAME_MS:
        raise ValueError("unsupported timeframe")
    if not 0.5 <= train_fraction <= 0.85:
        raise ValueError("train_fraction must be 0.5 to 0.85")
    if not isinstance(min_resolved, int) or min_resolved < 1:
        raise ValueError("min_resolved must be positive")
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
        "parameters_predeclared": True,
        "trading_ready": False,
        "warnings": [
            "No parameter selection, optimization, or threshold tuning performed",
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
        "adequate_sample": resolved >= minimum,
        "rebound_fraction": (
            round(counts["rebound"] / resolved, 4) if resolved >= minimum else None),
        "mean_pre_rebound_mae_pct": (
            round(sum(rebound_mae) / len(rebound_mae), 4)
            if rebound_mae and resolved >= minimum else None),
    }
