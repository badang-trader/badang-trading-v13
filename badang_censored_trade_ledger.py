"""Stage 81: stable censored-trade ledger and partition-boundary audit.

Prior run artifacts must be supplied separately for historical 29/27/28 ID diff.
Never assume that differing counts are due only to refreshed data.
"""
import json
from pathlib import Path
from collections import Counter
from badang_causal_mark_lookup import FRAME_MS

def audit(cases,histories):
    records=[]
    boundary_errors=[]
    for case in cases:
        symbol,frame=case["symbol"],case["timeframe"]
        rows=histories[(symbol,frame)]
        split=int(len(rows)*.7)
        for strategy in ("early","confirmed"):
            for index,t in enumerate(case["reversal_backtest"][strategy]["trades"]):
                if t["net_return"] is not None:continue
                entry=int(t["entry_bar"]);exit_bar=int(t["exit_bar"])
                partition=t["partition"];reason=t["exit_reason"]
                expected_end=split-1 if partition=="TRAIN" else len(rows)-1
                expected_reason="END_OF_PARTITION" if partition=="TRAIN" else "END_OF_DATA"
                if exit_bar!=expected_end or reason!=expected_reason or (partition=="TRAIN" and entry>=split) or (partition=="HOLDOUT" and entry<split):
                    boundary_errors.append({"symbol":symbol,"frame":frame,"strategy":strategy,"index":index,"error":"BOUNDARY"})
                entry_ts=int(rows[entry][0])
                records.append({"trade_id":f"{strategy}:{partition}:{symbol}:{frame}:{entry_ts}:{t['side']}",
                                "source_index":index,"symbol":symbol,"timeframe":frame,
                                "strategy":strategy,"partition":partition,"side":t["side"],
                                "entry_ts":entry_ts,"end_ts":int(rows[exit_bar][0])+FRAME_MS[frame],
                                "reason":reason})
    ids=[x["trade_id"] for x in records]
    duplicates=[k for k,v in Counter(ids).items() if v>1]
    counts=Counter(x["reason"] for x in records)
    return {"status":"PASS" if not (duplicates or boundary_errors) else "FAIL",
            "count":len(records),"by_reason":dict(counts),
            "duplicate_ids":duplicates,"boundary_errors":boundary_errors,
            "records":records,
            "historical_29_27_28_id_reconciliation":"NOT_VERIFIED_PREVIOUS_ARTIFACTS_REQUIRED",
            "warning":"CURRENT_DATASET_ONLY; NO HISTORICAL_ID_DIFF_OR_LIQUIDATION_PROOF"}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=audit(cases,histories)
    (folder/"bitget_censored_trade_ledger.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("censored trade ledger:",json.dumps({k:v for k,v in result.items() if k!="records"}))
    if result["status"]!="PASS":raise SystemExit("CENSORED TRADE BOUNDARY MISMATCH")
if __name__=="__main__":main()
