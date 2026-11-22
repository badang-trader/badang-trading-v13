"""Stage 91: causal higher-timeframe EMA candidate selection, research only."""
import json
from pathlib import Path
from badang_prospective_ema_eligibility import audit as same_frame_audit
from badang_reversal_multiframe_alignment import ORDER,completed_higher_index,ema_at_closed_index
from badang_historical_integrity import FRAME_MS

def audit(cases,histories):
    base=same_frame_audit(cases,histories)
    by_key={(c["symbol"],c["timeframe"]):c for c in cases}
    results=[]
    for market in base["results"]:
        symbol,frame,strategy=market["symbol"],market["timeframe"],market["strategy"]
        rows=histories[(symbol,frame)]
        for sample in market["sample_entries"]:
            raw=by_key[(symbol,frame)]["reversal_backtest"][strategy]["trades"][int(sample["trade_id"].rsplit(":",1)[-1])]
            signal_bar=int(raw["signal_bar"])
            signal_close=int(rows[signal_bar][0])+FRAME_MS[frame]
            entry=int(rows[int(raw["entry_bar"])][0])
            if signal_close>entry:
                raise AssertionError("signal close after entry")
            higher=ORDER[ORDER.index(frame)+1] if ORDER.index(frame)+1<len(ORDER) else None
            if higher is None:
                status="NO_HIGHER_TIMEFRAME"
                values=None
            else:
                hrows=histories[(symbol,higher)]
                index=completed_higher_index(hrows,higher,signal_close)
                if index<0:
                    values=None
                    status="INSUFFICIENT_HIGHER_HISTORY"
                else:
                    values=[ema_at_closed_index(hrows,index,n) for n in (20,50,200)]
                    if any(v is None for v in values) or index<199:
                        status="INSUFFICIENT_HIGHER_HISTORY"
                    else:
                        aligned=(values[0]>values[1]>values[2] if sample["side"]=="LONG"
                                 else values[0]<values[1]<values[2])
                        status="HTF_ALIGNED" if aligned else "HTF_EXCLUDED"
                    if int(hrows[index][0])+FRAME_MS[higher]>signal_close:
                        raise AssertionError("future higher candle used")
            results.append({"trade_id":sample["trade_id"],"symbol":symbol,"timeframe":frame,
                            "strategy":strategy,"side":sample["side"],"entry_ts":entry,
                            "signal_close_ts":signal_close,"higher_timeframe":higher,
                            "higher_ema20_50_200":values,"status":status,
                            "same_frame_ema_aligned":sample["ema_aligned"],
                            "censored":sample["net_return"] is None,
                            "closed_net_return":sample["net_return"]})
    if len(results)!=48:
        raise AssertionError(f"expected 48 post-cutoff candidates, got {len(results)}")
    categories={s:sum(x["status"]==s for x in results)
                for s in ("HTF_ALIGNED","HTF_EXCLUDED","INSUFFICIENT_HIGHER_HISTORY","NO_HIGHER_TIMEFRAME")}
    if sum(categories.values())!=len(results):
        raise AssertionError("candidate classification incomplete")
    return {"status":"PASS","cutoff_ms":base["cutoff_ms"],
            "candidate_count":len(results),"classification":categories,
            "results":results,
            "warnings":["CAUSAL_HTF_CANDIDATE_SELECTION_ONLY",
                        "NOT_PAIRED_HTF_EQUITY_OR_INDEPENDENT_PERFORMANCE",
                        "CENSORED_RETURNS_NOT_ZERO","NO_EXCHANGE_LIQUIDATION_MODEL"]}
def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=audit(cases,histories)
    (folder/"bitget_htf_ema_candidate_selection.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("HTF EMA candidate selection:",json.dumps(
        {k:v for k,v in result.items() if k!="results"}))
if __name__=="__main__":main()
