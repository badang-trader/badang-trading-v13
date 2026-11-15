"""Bounded, read-only Bitget historical expansion for research only.

Never used by the live scanner. Returns a strict contiguous suffix of real,
confirmed exchange candles; gaps and conflicting duplicate bars fail closed.
"""
import math
import re
import time
from bitget_market_data import FRAMES, _get

def research_history(symbol, timeframe, *, target_bars=1000, max_pages=6,
                     now_ms=None, fetch=None):
    if not re.fullmatch(r"[A-Z0-9]{2,25}USDT", symbol or ""):
        raise ValueError("Invalid Bitget symbol")
    if timeframe not in FRAMES:
        raise ValueError("Unsupported timeframe")
    if type(target_bars) is not int or not 205 <= target_bars <= 1400:
        raise ValueError("Research target outside bounded range")
    if type(max_pages) is not int or not 1 <= max_pages <= 6:
        raise ValueError("Research page budget outside bounded range")
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    if type(now_ms) is not int or now_ms <= 0:
        raise ValueError("Invalid research clock")
    granularity, step = FRAMES[timeframe]
    request = fetch if fetch is not None else _get
    seen = {}
    cursor = (now_ms // step) * step
    pages = 0
    stop = "page_budget"
    for _ in range(max_pages):
        raw = request("/api/v2/mix/market/history-candles", {
            "symbol": symbol, "productType": "USDT-FUTURES",
            "granularity": granularity, "endTime": str(cursor),
            "limit": "200"})
        pages += 1
        if not isinstance(raw, list):
            raise ValueError("Malformed Bitget historical page")
        if not raw:
            stop = "empty_page"
            break
        oldest = None
        added = 0
        for item in raw:
            if not isinstance(item, (list, tuple)) or len(item) < 6:
                raise ValueError("Malformed Bitget historical candle")
            try:
                stamp = int(item[0])
                if stamp < 100000000000:
                    stamp *= 1000
                o, h, l, c, v = map(float, item[1:6])
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("Invalid Bitget historical OHLCV") from exc
            if (stamp % step or stamp < 0 or stamp > now_ms + step or
                not all(math.isfinite(x) for x in (o, h, l, c, v)) or
                min(o, h, l, c) <= 0 or h < max(o, l, c) or
                l > min(o, c) or v < 0):
                raise ValueError("Invalid Bitget historical candle")
            if stamp + step > now_ms:
                continue  # exclude unconfirmed candle
            normalized = [str(stamp), str(o), str(h), str(l), str(c), str(v)]
            if stamp in seen:
                if seen[stamp] != normalized:
                    raise ValueError("Conflicting Bitget historical candle")
            else:
                seen[stamp] = normalized
                added += 1
            oldest = stamp if oldest is None else min(oldest, stamp)
        if oldest is None or oldest >= cursor or added == 0:
            stop = "no_older_confirmed_candles"
            break
        cursor = oldest
        if len(seen) >= target_bars:
            stop = "target_reached"
            break
    # A page with fewer than the requested 200 candles can still have a gap;
    # only the final consecutive suffix is eligible for research.
    stamps = sorted(seen)
    if not stamps:
        return {"status": "insufficient_history", "candles": [],
                "pages": pages, "stop_reason": stop, "trading_ready": False}
    contiguous = [stamps[-1]]
    for stamp in reversed(stamps[:-1]):
        if contiguous[-1] - stamp != step:
            stop = "historical_gap"
            break
        contiguous.append(stamp)
    contiguous.reverse()
    rows = [seen[t] for t in contiguous[-target_bars:]]
    # No stale, gapped, synthetic, or unconfirmed bars are marked adequate.
    fresh = now_ms - (int(rows[-1][0]) + step) <= 2 * step
    adequate = len(rows) >= target_bars and fresh
    return {"status": "ok" if adequate else "insufficient_history",
            "candles": rows, "confirmed_bars": len(rows),
            "pages": pages, "stop_reason": stop,
            "target_bars": target_bars, "fresh": fresh,
            "source": "Bitget USDT-FUTURES history-candles",
            "read_only": True, "trading_ready": False}
