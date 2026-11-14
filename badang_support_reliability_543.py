"""Conservative evidence grading for BTC/ETH historical support zones.

This is an explanatory evidence score, NOT a calibrated rebound probability.
All input candles must be confirmed, contiguous, and chronologically ordered.
No orders or position sizing.
"""
from __future__ import annotations
from math import isfinite
from badang_support_zones_541 import _candle, TIMEFRAMES, SYMBOLS
from badang_volume_profile_542 import support_volume_confluence


def evaluate_support_reliability(candles, symbol, timeframe, mode="scalp",
                                 *, confirmed=True):
    base = symbol.upper().split("-")[0].split("/")[0]
    if base not in SYMBOLS or mode not in TIMEFRAMES or timeframe not in TIMEFRAMES[mode]:
        raise ValueError("unsupported symbol/timeframe/mode")
    if not confirmed:
        return {"status": "unconfirmed", "zones": [], "trading_ready": False}
    result = support_volume_confluence(candles, symbol, timeframe, mode,
                                       confirmed=confirmed)
    if result["status"] != "ok":
        return {"status": result["status"], "zones": [], "trading_ready": False}
    try:
        rows = [_candle(c) for c in candles]
    except (ValueError, TypeError, OverflowError):
        return {"status": "invalid_data", "zones": [], "trading_ready": False}
    evaluated = []
    for zone in result["zones"]:
        age = zone["last_touch_age_bars"]
        last_pivot_idx = len(rows) - 1 - age
        # Only events after the latest confirmed pivot can invalidate this
        # particular support episode. A single confirmed close below the lower
        # boundary is a breakdown; a subsequent recovery does not erase it.
        later = rows[last_pivot_idx + 1:]
        breaches = sum(bar["close"] < zone["lower"] for bar in later)
        touches = zone["pivot_touches"]
        vol = zone["relative_volume_at_zone"]
        score = 30
        reasons = []
        score += min(touches, 4) * 10
        reasons.append(f"{touches} confirmed pivot touches")
        if age <= 30:
            score += 10
            reasons.append("recent confirmed pivot")
        elif age > 100:
            score -= 15
            reasons.append("stale support")
        if vol is not None and isfinite(vol) and vol >= 0.7:
            score += 10
            reasons.append("overlap with high estimated-volume node")
        else:
            reasons.append("no strong volume-profile confluence")
        if breaches:
            score -= 60
            reasons.append(f"{breaches} confirmed closes below zone after pivot")
        score = max(0, min(100, score))
        status = "broken" if breaches else "historical_support"
        # Evidence bands are heuristic, not empirical success probabilities.
        grade = ("invalidated" if breaches else
                 "strong_evidence" if score >= 80 else
                 "moderate_evidence" if score >= 60 else "limited_evidence")
        evaluated.append({**zone, "evidence_score": score,
                          "evidence_grade": grade, "status": status,
                          "confirmed_close_breaches": breaches,
                          "evidence_reasons": reasons,
                          "rebound_probability": None})
    # Broken levels remain visible as risk information but are ranked last.
    evaluated.sort(key=lambda z: (z["status"] == "broken",
                                  -z["evidence_score"], -z["center"]))
    return {"status": "ok", "symbol": base, "timeframe": timeframe,
            "mode": mode, "zones": evaluated,
            "trading_ready": False,
            "warnings": ["Evidence score is heuristic, not a win rate",
                         "OHLCV volume profile approximates volume at price",
                         "Broken supports are not automatic buy levels",
                         "Confirm source timestamps and contiguous closed candles"]}


def multi_timeframe_reliability(series_by_timeframe, symbol, mode="scalp",
                                *, confirmed=True):
    if mode not in TIMEFRAMES:
        raise ValueError("unsupported mode")
    return {tf: evaluate_support_reliability(
        series_by_timeframe.get(tf, []), symbol, tf, mode, confirmed=confirmed)
        for tf in TIMEFRAMES[mode]}
