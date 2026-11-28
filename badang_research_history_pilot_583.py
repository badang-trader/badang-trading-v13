"""Explicit, bounded read-only Bitget history pilot; no trading or deployment."""
import json
import sys
import time
from badang_research_history_582 import research_history

TARGETS = (("BTCUSDT", "15m"), ("ETHUSDT", "15m"),
           ("BTCUSDT", "1H"), ("ETHUSDT", "1H"))

def pilot(*, fetcher=None):
    results = []
    for symbol, frame in TARGETS:
        start = time.monotonic()
        item = {"symbol": symbol, "timeframe": frame}
        try:
            kw = {"target_bars": 1000, "max_pages": 6}
            if fetcher is not None:
                kw["fetch"] = fetcher
            result = research_history(symbol, frame, **kw)
            item.update({k: result.get(k) for k in
                         ("status", "confirmed_bars", "pages", "stop_reason",
                          "fresh", "target_bars")})
        except Exception as exc:
            item["status"] = "error"
            item["error_type"] = type(exc).__name__
            item["error_message"] = str(exc)[:160]
        if item["status"] == "ok":
            item["result_category"] = "adequate"
        elif item["status"] == "error":
            message = str(item.get("error_message", "")).lower()
            item["result_category"] = ("rate_limited" if "429" in message or "요청 제한" in message
                                       else "request_or_data_error")
        else:
            item["result_category"] = "insufficient_or_stale_history"
        item["elapsed_ms"] = round((time.monotonic() - start) * 1000)
        results.append(item)
    return {"read_only": True, "trading_ready": False,
            "target_count": len(TARGETS),
            "adequate_targets": sum(x["status"] == "ok" for x in results),
            "results": results}

if __name__ == "__main__":
    report = pilot()
    with open("badang-research-history-pilot.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    sys.exit(0 if report["adequate_targets"] == report["target_count"] else 2)
