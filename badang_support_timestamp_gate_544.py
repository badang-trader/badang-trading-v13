"""Strict timestamp and confirmed-bar gate for BTC/ETH support research.

Callers must supply the exchange's last *closed* bar timestamp and a trusted
exchange/server clock. A local wall clock is not a substitute for exchange time.
"""
from __future__ import annotations
from datetime import datetime, timezone
from badang_support_reliability_543 import evaluate_support_reliability

FRAME_MS = {"15m": 900000, "30m": 1800000, "1h": 3600000,
            "4h": 14400000, "1d": 86400000}


def _timestamp_ms(value):
    if isinstance(value, bool):
        raise ValueError("boolean timestamp")
    if isinstance(value, (int, float)):
        if not (value == value and abs(value) != float("inf")):
            raise ValueError("non-finite timestamp")
        if not value.is_integer() if isinstance(value, float) else False:
            raise ValueError("fractional timestamp")
        return int(value)
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise ValueError("timestamp must be epoch milliseconds")


def validated_support_reliability(candles, symbol, timeframe, mode="scalp",
                                  *, exchange_now_ms):
    """Reject missing, duplicate, future, open, or non-contiguous timestamps.

    Timestamp is candle *opening* epoch ms, as in standard exchange OHLCV.
    """
    if not isinstance(timeframe, str) or timeframe not in FRAME_MS:
        raise ValueError("unsupported timeframe")
    if not isinstance(candles, (list, tuple)) or len(candles) < 60:
        return {"status": "insufficient_history", "zones": [], "trading_ready": False}
    now = _timestamp_ms(exchange_now_ms)
    interval = FRAME_MS[timeframe]
    times = []
    for row in candles:
        try:
            if isinstance(row, dict):
                raw = row.get("timestamp", row.get("ts"))
            elif isinstance(row, (tuple, list)) and len(row) >= 6:
                raw = row[0]
            else:
                raise ValueError("missing timestamp")
            times.append(_timestamp_ms(raw))
        except (ValueError, TypeError, OverflowError):
            return {"status": "invalid_timestamp", "zones": [], "trading_ready": False}
    if any(t < 0 or t % interval != 0 for t in times):
        return {"status": "misaligned_timestamp", "zones": [], "trading_ready": False}
    if any(b - a != interval for a, b in zip(times, times[1:])):
        return {"status": "noncontiguous_history", "zones": [], "trading_ready": False}
    if times[-1] + interval > now:
        return {"status": "open_or_future_candle", "zones": [], "trading_ready": False}
    result = evaluate_support_reliability(candles, symbol, timeframe, mode)
    result["timestamp_integrity"] = "verified" if result["status"] == "ok" else "rejected"
    return result
