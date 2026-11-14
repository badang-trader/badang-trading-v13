"""Causal support-zone touch outcome research; no live orders.

At each bar t, build zones ONLY from bars before t. Evaluate whether a
subsequent touch was followed by a rebound or breakdown within a fixed horizon.
Rebound and breakdown require confirmed closes, not intrabar wick highs.
Not a calibrated trading signal or win-rate claim without adequate samples.
"""
from __future__ import annotations
import math
from badang_support_timestamp_gate_544 import validated_support_reliability, FRAME_MS
from badang_support_zones_541 import _candle


def support_touch_backtest(candles, symbol, timeframe, mode="scalp",
                           *, horizon=8, warmup=90, rebound_pct=0.5,
                           max_events=300, exchange_now_ms=None):
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 48:
        raise ValueError("invalid horizon")
    if isinstance(warmup, bool) or not isinstance(warmup, int) or warmup < 60:
        raise ValueError("invalid warmup")
    if isinstance(max_events, bool) or not isinstance(max_events, int) or not 1 <= max_events <= 1000:
        raise ValueError("invalid event cap")
    if (isinstance(rebound_pct, bool) or
            not isinstance(rebound_pct, (int, float)) or
            not math.isfinite(rebound_pct) or not 0 < rebound_pct <= 20):
        raise ValueError("invalid rebound threshold")
    if timeframe not in FRAME_MS:
        raise ValueError("unsupported timeframe")
    if len(candles) < warmup + horizon + 1:
        return {"status": "insufficient_history", "events": [], "trading_ready": False}
    if exchange_now_ms is None:
        return {"status": "missing_exchange_clock", "events": [], "trading_ready": False}
    # Validate the *entire* sample before measuring anything.
    validation = validated_support_reliability(
        candles, symbol, timeframe, mode,
        exchange_now_ms=exchange_now_ms)
    if validation["status"] != "ok":
        return {"status": validation["status"], "events": [], "trading_ready": False}
    rows = [_candle(c) for c in candles]
    events = []
    i = warmup
    while i + horizon < len(rows) and len(events) < max_events:
        # Prior bars ONLY; excludes touch bar and future outcome window.
        prior = candles[:i]
        ref = validated_support_reliability(
            prior, symbol, timeframe, mode,
            exchange_now_ms=_end_of_last_bar(prior, timeframe))
        if ref["status"] != "ok":
            return {"status": ref["status"], "events": [], "trading_ready": False}
        # Restrict to historically intact support zones.
        zones = [z for z in ref["zones"] if z["status"] == "historical_support"]
        # No look-ahead: select the closest historical zone intersecting touch bar.
        touched = [z for z in zones if rows[i]["low"] <= z["upper"]
                   and rows[i]["high"] >= z["lower"]]
        if not touched:
            i += 1
            continue
        zone = min(touched, key=lambda z: abs(z["center"] - rows[i-1]["close"]))
        rebound_level = zone["upper"] * (1 + rebound_pct / 100)
        # A break is a confirmed close below zone lower, not intrabar wick.
        outcome = "breakdown_on_touch" if rows[i]["close"] < zone["lower"] else "unresolved"
        outcome_bar_index = i if outcome == "breakdown_on_touch" else None
        if outcome != "breakdown_on_touch":
            for j in range(i + 1, i + horizon + 1):
                bar = rows[j]
                rebound = bar["close"] >= rebound_level
                break_down = bar["close"] < zone["lower"]
                if break_down:
                    outcome = "breakdown"
                    outcome_bar_index = j
                    break
                if rebound:
                    outcome = "rebound"
                    outcome_bar_index = j
                    break
        # Fixed-horizon MAE includes all bars; pre-outcome MAE stops at
        # the first confirmed rebound or breakdown, including its candle.
        window = rows[i:i + horizon + 1]
        worst_low = min(bar["low"] for bar in window)
        adverse_pct = max(0.0, (zone["upper"] - worst_low) / zone["upper"] * 100)
        end = outcome_bar_index if outcome_bar_index is not None else i + horizon
        pre_outcome_low = min(bar["low"] for bar in rows[i:end + 1])
        pre_outcome_adverse_pct = max(
            0.0, (zone["upper"] - pre_outcome_low) / zone["upper"] * 100)
        events.append({"touch_bar_index": i, "zone_lower": zone["lower"],
                       "zone_upper": zone["upper"],
                       "evidence_score_at_touch": zone["evidence_score"],
                       "outcome": outcome,
                       "outcome_bar_index": outcome_bar_index,
                       "pre_outcome_max_adverse_excursion_pct": round(pre_outcome_adverse_pct, 4),
                       "max_adverse_excursion_pct": round(adverse_pct, 4)})
        # Non-overlapping evaluation windows avoid repeated counting.
        i += horizon + 1
    scan_complete = i + horizon >= len(rows)
    counts = {name: sum(e["outcome"] == name for e in events)
              for name in ("rebound", "breakdown", "breakdown_on_touch", "ambiguous", "unresolved")}
    resolved = counts["rebound"] + counts["breakdown"] + counts["breakdown_on_touch"]
    # Separate adverse excursions by realized first outcome; no pooling
    # successes with failed supports.
    adverse_by_outcome = {}
    for label in ("rebound", "breakdown", "breakdown_on_touch", "unresolved"):
        values = [e["pre_outcome_max_adverse_excursion_pct"]
                  for e in events if e["outcome"] == label]
        adverse_by_outcome[label] = {
            "count": len(values),
            "mean_pre_outcome_mae_pct": (
                round(sum(values) / len(values), 4) if values else None),
            "max_pre_outcome_mae_pct": max(values) if values else None,
        }
    return {"status": "ok", "symbol": symbol, "timeframe": timeframe,
            "horizon_bars": horizon, "rebound_threshold_pct": rebound_pct,
            "outcome_basis": "confirmed close only; no intrabar wick credit",
            "events": events, "counts": counts,
            "scan_complete": scan_complete,
            "event_cap_reached": not scan_complete and len(events) >= max_events,
            "resolved_events": resolved,
            "adverse_excursion_by_outcome": adverse_by_outcome,
            "mean_pre_outcome_max_adverse_excursion_pct": (
                round(sum(e["pre_outcome_max_adverse_excursion_pct"] for e in events) / len(events), 4)
                if events else None),
            "mean_max_adverse_excursion_pct": (
                round(sum(e["max_adverse_excursion_pct"] for e in events) / len(events), 4)
                if events else None),
            "observed_rebound_fraction": (
                round(counts["rebound"] / resolved, 4) if resolved >= 30 else None),
            "sample_adequate": resolved >= 30,
            "trading_ready": False,
            "warnings": ["Historical in-sample description only, not forward accuracy",
                         "Insufficient resolved events suppresses rebound fraction",
                         "Threshold and horizon are research parameters",
                         "Transaction costs and slippage not modeled"]}


def _end_of_last_bar(candles, timeframe):
    last = candles[-1]
    raw = last.get("timestamp", last.get("ts")) if isinstance(last, dict) else last[0]
    try:
        ts = int(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid last timestamp") from exc
    return ts + FRAME_MS[timeframe]
