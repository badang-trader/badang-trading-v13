"""Stage 74: replay historical reversal signals using only prefix-available bars.

Read-only Bitget OHLCV research; does not assert independent profitability.
"""
import json
from pathlib import Path
from badang_reversal_backtest import reversal_signals

def audit_market(rows, symbol, timeframe):
    full={kind:reversal_signals(rows,kind) for kind in ("EARLY","CONFIRMED")}
    # Audit each signal availability time, plus periodic no-signal prefixes.
    checkpoints={len(rows)}
    for kind in full:
        checkpoints.update(int(s["bar"])+1 for s in full[kind])
    checkpoints.update(range(50,len(rows)+1,25))
    mismatches=[]
    tested=0
    for n in sorted(x for x in checkpoints if 1<=x<=len(rows)):
        for kind in ("EARLY","CONFIRMED"):
            expected=[s for s in full[kind] if int(s["bar"])<n]
            # Last signal bar is excluded by reversal_signals if no next-open
            # candle exists in this prefix; compare only executable signals.
            expected=[s for s in expected if int(s["bar"])+1<n]
            actual=reversal_signals(rows[:n],kind)
            tested+=1
            if actual!=expected:
                mismatches.append({"prefix_bars":n,"kind":kind,
                                   "expected":len(expected),"actual":len(actual),
                                   "expected_sample":expected[:2],"actual_sample":actual[:2]})
    return {"symbol":symbol,"timeframe":timeframe,"bars":len(rows),
            "prefix_checkpoints":len(checkpoints),"comparisons":tested,
            "early_signals":len(full["EARLY"]),"confirmed_signals":len(full["CONFIRMED"]),
            "mismatches":mismatches[:10],"mismatch_count":len(mismatches),
            "status":"PASS" if not mismatches else "FAIL"}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    output=[]
    for case in cases:
        symbol,frame=case["symbol"],case["timeframe"]
        rows=json.loads((folder/f"bitget_{symbol}_{frame}.json").read_text(encoding="utf-8"))["candles"]
        output.append(audit_market(rows,symbol,frame))
    result={"status":"PASS" if all(x["status"]=="PASS" for x in output) else "FAIL",
            "markets":output,"comparisons":sum(x["comparisons"] for x in output),
            "mismatches":sum(x["mismatch_count"] for x in output),
            "warning":"SIGNAL_PREFIX_ONLY; DOES_NOT_PROVE_PROSPECTIVE_PROFITABILITY"}
    (folder/"bitget_reversal_prefix_replay.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("causal prefix replay:",json.dumps(
        {k:v for k,v in result.items() if k!="markets"}))
    for row in output:
        print("causal prefix market:",json.dumps(
            {k:v for k,v in row.items() if k!="mismatches"}))
    if result["status"]!="PASS":
        raise SystemExit("CAUSAL PREFIX SIGNAL MISMATCH")
if __name__=="__main__":main()
