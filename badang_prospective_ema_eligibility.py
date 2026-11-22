"""Prospective eligibility audit. Historical warmup is never scored as new performance.
Research-only; no orders. This does not assert EMA profitability.
"""
import json
from collections import Counter
from pathlib import Path
from badang_prospective_holdout_gate import cutoff_ms
from badang_causal_mark_lookup import FRAME_MS

def ema(values, span):
    alpha=2/(span+1)
    result=[]
    previous=None
    for value in values:
        previous=value if previous is None else alpha*value+(1-alpha)*previous
        result.append(previous)
    return result

def audit(cases, histories):
    cutoff=cutoff_ms()
    output=[]
    for case in cases:
        symbol,frame=case["symbol"],case["timeframe"]
        rows=histories[(symbol,frame)]
        opens=[int(r[0]) for r in rows]
        if opens!=sorted(set(opens)):
            raise ValueError("unordered or duplicate bars")
        closes=[float(r[4]) for r in rows]
        e20,e50,e200=(ema(closes,n) for n in (20,50,200))
        for strategy in ("early","confirmed"):
            counts=Counter()
            samples=[]
            for trade in case["reversal_backtest"][strategy]["trades"]:
                i=int(trade["entry_bar"])
                if not 0<=i<len(rows):
                    raise ValueError("invalid entry")
                if opens[i]<=cutoff:
                    counts["PRE_CUTOFF_EXCLUDED"]+=1
                    continue
                counts["POST_CUTOFF_CANDIDATE"]+=1
                # EMA values must be available before entry: last fully closed candle.
                prior=i-1
                if prior<199 or opens[prior]+FRAME_MS[frame]>opens[i]:
                    counts["EMA_INSUFFICIENT_HISTORY"]+=1
                    continue
                side=trade["side"]
                aligned=(e20[prior]>e50[prior]>e200[prior] if side=="LONG"
                         else e20[prior]<e50[prior]<e200[prior] if side=="SHORT"
                         else None)
                if aligned is None:
                    raise ValueError("invalid side")
                counts["EMA_ALIGNED" if aligned else "EMA_EXCLUDED"]+=1
                samples.append({"entry_ts":opens[i],"side":side,"ema_aligned":aligned,
                                "entry_bar":i,"exit_reason":trade["exit_reason"],
                                "net_return":trade["net_return"],
                                "note":"NOT_PROSPECTIVE_OUTCOME_VALIDATED"})
            output.append({"symbol":symbol,"timeframe":frame,"strategy":strategy,
                           "counts":dict(counts),"sample_entries":samples,
                           "higher_timeframe_filter":"NOT_EVALUATED",
                           "independent_performance":"NOT_ESTABLISHED"})
    return {"cutoff_ms":cutoff,"warmup_only_before_cutoff":True,
            "ema_rule":"previous closed candle EMA20>EMA50>EMA200 for LONG; reverse for SHORT",
            "warning":"Historical 70/30 candidate selection and exits cannot certify prospective performance",
            "results":output}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    report=audit(cases,histories)
    (folder/"bitget_prospective_ema_eligibility.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    totals=Counter()
    for row in report["results"]:
        totals.update(row["counts"])
    print("prospective EMA eligibility:",json.dumps(dict(totals)))
    print("independent EMA profitability: NOT_ESTABLISHED")
if __name__=="__main__":
    main()
