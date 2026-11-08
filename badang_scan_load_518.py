"""Read-only production-shaped /api/scan load check; no orders or database."""
import concurrent.futures
import json
import os
import resource
import time
import tracemalloc

os.environ["BADANG_TRADING_ENABLED"] = "false"
os.environ["DATABASE_URL"] = ""
import app

tracemalloc.start()
records=[]
def one(offset, mode):
    started=time.monotonic()
    with app.app.test_client() as client:
        response=client.get("/api/scan",query_string={
            "mode":mode,"offset":offset,"min_turnover":10000000})
        payload=response.get_json(silent=True) or {}
    return {
        "mode":mode,"offset":offset,"http":response.status_code,
        "elapsed_s":round(time.monotonic()-started,2),
        "results":len(payload.get("results",[])),
        "errors":len(payload.get("errors",[])),
        "total":payload.get("total"),
        "error_samples":[x.get("error","")[:100] for x in payload.get("errors",[])[:3]],
        "rss_mb":round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),
    }
start=time.monotonic()
# Production route uses 2 internal workers per request. Keep external load bounded.
for offset,mode in ((0,"scalp"),(5,"scalp")):
    row=one(offset,mode)
    records.append(row)
    print("SCAN_SAMPLE",json.dumps(row),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for row in pool.map(lambda args:one(*args),[(0,"scalp"),(5,"scalp")]):
        records.append(row)
        print("SCAN_SAMPLE",json.dumps(row),flush=True)
current,peak=tracemalloc.get_traced_memory()
summary={
    "scope":"isolated_GitHub_Actions_real_public_API_scan_route",
    "trading_enabled":False,"requests":len(records),
    "http_200":sum(r["http"]==200 for r in records),
    "symbol_results":sum(r["results"] for r in records),
    "symbol_errors":sum(r["errors"] for r in records),
    "peak_rss_mb":round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),
    "tracemalloc_peak_mb":round(peak/1048576,2),
    "elapsed_s":round(time.monotonic()-start,2),
    "records":records,
}
with open("badang-scan-load.json","w") as f:json.dump(summary,f,indent=2)
print("SCAN_SUMMARY",json.dumps({k:v for k,v in summary.items() if k!="records"}),flush=True)
if summary["http_200"]!=len(records) or summary["symbol_errors"]:
    raise SystemExit("Scan route failed or produced symbol errors")
