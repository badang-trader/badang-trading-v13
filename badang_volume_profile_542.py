"""Read-only approximate volume profile and confluence for BTC/ETH.

OHLCV bar volume is uniformly allocated across each candle's high-low range.
This is NOT order-book depth, cost basis, or actual traded volume at price.
Requires independently validated, contiguous, confirmed candles per timeframe.
"""
from __future__ import annotations
from math import isfinite
from badang_support_zones_541 import support_zones, _candle, TIMEFRAMES, SYMBOLS


def approximate_volume_profile(candles, *, bins=48, lookback=240):
    if not isinstance(bins, int) or not 12 <= bins <= 200:
        raise ValueError("invalid bins")
    if not isinstance(lookback, int) or not 60 <= lookback <= 2000:
        raise ValueError("invalid lookback")
    if len(candles) < 60:
        return {"status": "insufficient_history", "levels": []}
    try:
        rows = [_candle(c) for c in candles[-lookback:]]
    except (ValueError, TypeError, OverflowError):
        return {"status": "invalid_data", "levels": []}
    lo = min(r["low"] for r in rows)
    hi = max(r["high"] for r in rows)
    span = hi - lo
    if not isfinite(span) or span <= 0:
        return {"status": "zero_range", "levels": []}
    step = span / bins
    volumes = [0.0] * bins
    for row in rows:
        # Approximation: equal volume density throughout the observed bar range.
        # Flat bars assign their full volume to their close's bin.
        if row["high"] == row["low"]:
            index = min(bins - 1, max(0, int((row["close"] - lo) / step)))
            volumes[index] += row["volume"]
            continue
        density = row["volume"] / (row["high"] - row["low"])
        first = max(0, int((row["low"] - lo) / step))
        last = min(bins - 1, int((row["high"] - lo) / step))
        for i in range(first, last + 1):
            left = lo + i * step
            right = left + step
            overlap = max(0.0, min(row["high"], right) - max(row["low"], left))
            if overlap:
                volumes[i] += density * overlap
    if not all(isfinite(v) and v >= 0 for v in volumes):
        return {"status": "invalid_volume", "levels": []}
    peak = max(volumes)
    levels = [{"lower": round(lo + i * step, 8),
               "upper": round(lo + (i + 1) * step, 8),
               "center": round(lo + (i + 0.5) * step, 8),
               "estimated_volume": round(v, 4),
               "relative_volume": round(v / peak, 4) if peak else 0.0}
              for i, v in enumerate(volumes)]
    poc = max(levels, key=lambda x: x["estimated_volume"]) if peak else None
    return {"status": "ok", "levels": levels, "poc": poc,
            "method": "uniform candle-range allocation; estimated not traded-at-price",
            "bars_used": len(rows), "trading_ready": False}


def support_volume_confluence(candles, symbol, timeframe, mode="scalp",
                              *, confirmed=True, bins=48):
    """Overlay independent pivot/ATR support zones with estimated volume nodes.

    Does not promote weak levels to trade signals. Overlap is descriptive.
    """
    base = symbol.upper().split("-")[0].split("/")[0]
    if base not in SYMBOLS or mode not in TIMEFRAMES or timeframe not in TIMEFRAMES[mode]:
        raise ValueError("unsupported symbol/timeframe/mode")
    support = support_zones(candles, symbol, timeframe, mode, confirmed=confirmed)
    if support["status"] != "ok":
        return {"status": support["status"], "zones": [], "trading_ready": False}
    profile = approximate_volume_profile(candles, bins=bins)
    if profile["status"] != "ok":
        return {"status": profile["status"], "zones": [], "trading_ready": False}
    enriched = []
    for zone in support["zones"]:
        overlaps = [v for v in profile["levels"]
                    if v["lower"] < zone["upper"] and v["upper"] > zone["lower"]]
        strongest = max(overlaps, key=lambda v: v["relative_volume"]) if overlaps else None
        enriched.append({**zone,
                         "volume_profile_overlap": bool(overlaps),
                         "relative_volume_at_zone": (
                             strongest["relative_volume"] if strongest else None),
                         "volume_node": (
                             "high_estimated_volume" if strongest and
                             strongest["relative_volume"] >= 0.7 else
                             "ordinary_or_low_estimated_volume" if strongest else "none"),
                         "confidence_note": "Historical confluence, not rebound probability"})
    return {"status": "ok", "symbol": base, "timeframe": timeframe, "mode": mode,
            "zones": enriched, "poc": profile["poc"],
            "method": profile["method"], "trading_ready": False,
            "warnings": ["OHLCV-derived volume profile is an approximation",
                         "Cannot infer trapped holders or actual resting sell orders",
                         "No orders, averaging down, or execution recommendations"]}


def multi_timeframe_confluence(series_by_timeframe, symbol, mode="scalp",
                               *, confirmed=True):
    if mode not in TIMEFRAMES:
        raise ValueError("unsupported mode")
    return {tf: support_volume_confluence(series_by_timeframe.get(tf, []),
                                         symbol, tf, mode, confirmed=confirmed)
            for tf in TIMEFRAMES[mode]}
