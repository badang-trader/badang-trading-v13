"""Bounded read-only live-data endurance measurement; never places orders.

Runs inside isolated GitHub Actions, not the production Render service.
"""
import json
import os
import resource
import statistics
import time
import tracemalloc
from bitget_market_data import fastest_candles
from badang_analysis_v13 import analyze

os.environ["BADANG_TRADING_ENABLED"] = "false"
os.environ["DATABASE_URL"] = ""
tracemalloc.start()
samples = []
started = time.monotonic()
symbols = ("BTCUSDT", "ETHUSDT")
frames = ("15m", "1H")
for cycle in range(20):
    for symbol in symbols:
        for frame in frames:
            t0 = time.monotonic()
            row = {"cycle": cycle + 1, "symbol": symbol, "frame": frame}
            try:
                market = fastest_candles(symbol, frame, exchanges=["bitget"])
                assert market["exchange"] == "bitget"
                candles = market["candles"]
                result = analyze(candles[:-1], mode="scalp", symbol=symbol)
                row.update(ok=result.get("status") == "ok",
                           bars=len(candles)-1,
                           analysis_status=result.get("status"),
                           exchange=market["exchange"])
            except Exception as exc:
                row.update(ok=False, error_type=type(exc).__name__,
                           error=str(exc)[:180])
            row["elapsed_s"] = round(time.monotonic()-t0, 3)
            row["rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024, 2)
            samples.append(row)
            print("SAMPLE", json.dumps(row, ensure_ascii=False), flush=True)
    time.sleep(1)
current, peak = tracemalloc.get_traced_memory()
ok = [s for s in samples if s["ok"]]
report = {
    "scope": "isolated_GitHub_Actions_read_only_public_Bitget",
    "trading_enabled": False, "cycles": 20, "requests": len(samples),
    "successes": len(ok), "failures": len(samples)-len(ok),
    "total_elapsed_s": round(time.monotonic()-started, 2),
    "mean_success_elapsed_s": round(statistics.mean(s["elapsed_s"] for s in ok), 3) if ok else None,
    "max_sample_elapsed_s": max(s["elapsed_s"] for s in samples),
    "peak_process_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024, 2),
    "peak_tracemalloc_mb": round(peak/1048576, 2),
    "samples": samples,
}
with open("badang-live-benchmark.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("BENCHMARK_SUMMARY", json.dumps({k:v for k,v in report.items() if k!="samples"}), flush=True)
if len(ok) != len(samples):
    raise SystemExit("Live read-only benchmark had failed samples")
