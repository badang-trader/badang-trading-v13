"""Read-only BTC/ETH support-zone research using confirmed OHLCV candles.

This module does not place orders, suggest position sizes, or average down.
Call once per confirmed timeframe; never mix candle intervals in one series.
"""
from __future__ import annotations

from math import isfinite
from statistics import median

TIMEFRAMES = {"scalp": ("15m", "30m", "1h"), "swing": ("1h", "4h", "1d")}
SYMBOLS = {"BTC", "ETH"}


def _candle(raw):
    if isinstance(raw, dict):
        fields = (raw.get(k) for k in ("open", "high", "low", "close", "volume"))
    elif isinstance(raw, (list, tuple)) and len(raw) >= 6:
        fields = raw[1:6]
    else:
        raise ValueError("invalid candle shape")
    try:
        o, h, l, c, v = (float(x) for x in fields)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("non-numeric candle") from exc
    if not all(isfinite(x) for x in (o, h, l, c, v)):
        raise ValueError("non-finite candle")
    if l <= 0 or v < 0 or l > min(o, c) or h < max(o, c) or h < l:
        raise ValueError("invalid OHLCV")
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def support_zones(candles, symbol, timeframe, mode="scalp", *, confirmed=True,
                  radius=3, max_zones=5):
    """Return historical support zones below last close; never an entry signal.

    Caller must verify source timestamps, equal bar spacing and closed-bar status.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("invalid symbol")
    base = symbol.upper().split("-")[0].split("/")[0]
    if base not in SYMBOLS or mode not in TIMEFRAMES or timeframe not in TIMEFRAMES[mode]:
        raise ValueError("unsupported symbol/timeframe/mode")
    if not confirmed:
        return {"status": "unconfirmed", "zones": [], "trading_ready": False}
    if isinstance(radius, bool) or not isinstance(radius, int) or not 2 <= radius <= 10:
        raise ValueError("invalid pivot radius")
    if isinstance(max_zones, bool) or not isinstance(max_zones, int) or not 1 <= max_zones <= 5:
        raise ValueError("invalid zone limit")
    if not isinstance(candles, (list, tuple)):
        return {"status": "invalid_data", "zones": [], "trading_ready": False}
    if len(candles) < 60:
        return {"status": "insufficient_history", "zones": [], "trading_ready": False}
    try:
        rows = [_candle(c) for c in candles]
    except ValueError:
        return {"status": "invalid_data", "zones": [], "trading_ready": False}
    close = rows[-1]["close"]
    true_ranges = []
    for i in range(1, len(rows)):
        bar, prev = rows[i], rows[i-1]
        true_ranges.append(max(bar["high"] - bar["low"],
                               abs(bar["high"] - prev["close"]),
                               abs(bar["low"] - prev["close"])))
    atr = median(true_ranges[-14:])
    if not isfinite(atr) or atr <= 0:
        return {"status": "zero_volatility", "zones": [], "trading_ready": False}
    width = max(atr * 0.35, close * 0.0005)
    pivots = []
    for i in range(radius, len(rows) - radius):
        low = rows[i]["low"]
        segment = [r["low"] for r in rows[i-radius:i+radius+1]]
        if low == min(segment) and segment.count(low) == 1 and low < close:
            pivots.append((i, low))
    # Cluster historical pivot lows, keeping one touch per pivot.
    clusters = []
    for idx, price in sorted(pivots, key=lambda p: p[1], reverse=True):
        cluster = next((c for c in clusters if abs(price - c["center"]) <= width), None)
        if cluster is None:
            clusters.append({"center": price, "prices": [price], "indices": [idx]})
        else:
            cluster["prices"].append(price)
            cluster["indices"].append(idx)
            cluster["center"] = median(cluster["prices"])
    zones = []
    for c in clusters:
        center = median(c["prices"])
        lower = max(0.0, center - width)
        upper = center + width
        if upper >= close:
            continue
        # A historical zone is not active after a later confirmed close breaks it.
        # Check from its most recent pivot; older broken levels must not reappear.
        last_pivot = max(c["indices"])
        if any(row["close"] < lower for row in rows[last_pivot + 1:]):
            continue
        touches = len(c["indices"])
        age = len(rows) - 1 - max(c["indices"])
        strength = "high" if touches >= 3 and age <= 80 else (
            "medium" if touches >= 2 else "low")
        zones.append({"lower": round(lower, 8), "upper": round(upper, 8),
                      "center": round(center, 8), "pivot_touches": touches,
                      "last_touch_age_bars": age, "strength": strength,
                      "distance_below_price_pct": round((close-center)/close*100, 2),
                      "basis": "confirmed pivot lows / ATR width",
                      "invalidated_if": "confirmed close below lower boundary"})
    zones.sort(key=lambda z: z["center"], reverse=True)
    return {"status": "ok", "symbol": base, "timeframe": timeframe, "mode": mode,
            "reference_close": close, "atr_proxy": round(atr, 8),
            "zones": zones[:max_zones], "trading_ready": False,
            "warnings": ["Research zones only; not automatic orders",
                         "Confirm timestamps, contiguous bars, and higher timeframe",
                         "Historical support can fail; no guaranteed fill or rebound"]}


def multi_timeframe_support(series_by_timeframe, symbol, mode="scalp"):
    """Input is a mapping of timeframe to independently confirmed candles."""
    if mode not in TIMEFRAMES:
        raise ValueError("unsupported mode")
    results = {tf: support_zones(series_by_timeframe.get(tf, []), symbol, tf, mode)
               for tf in TIMEFRAMES[mode]}
    # Annotate only confirmed, independently computed overlapping zones.
    # Never invent an additional price level or imply a guaranteed rebound.
    for tf, result in results.items():
        if result["status"] != "ok":
            continue
        for zone in result["zones"]:
            overlaps = []
            for other_tf, other_result in results.items():
                if other_tf == tf or other_result["status"] != "ok":
                    continue
                if any(other["lower"] <= zone["upper"] and
                       zone["lower"] <= other["upper"]
                       for other in other_result["zones"]):
                    overlaps.append(other_tf)
            zone["overlapping_timeframes"] = overlaps
            zone["timeframe_confluence_count"] = 1 + len(overlaps)
    return results
