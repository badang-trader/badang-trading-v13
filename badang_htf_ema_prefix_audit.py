"""Stage 79: verify higher-timeframe EMA values with entry-time prefixes.

No orders. Diagnostic only; no independent profitability assertion.
"""
import json
from pathlib import Path
from badang_historical_integrity import FRAME_MS
from badang_reversal_multiframe_alignment import ORDER,completed_higher_index,ema_at_closed_index
from badang_prospective_holdout_gate import cutoff_ms

def audit(cases,histories):
    cutoff=cutoff_ms()
    checks=0
    mismatches=[]
    insufficient=0
    no_higher=0
    opportunities=0
    by_market=[]
    for case in cases:
        symbol,frame=case["symbol"],case["timeframe"]
        rows=histories[(symbol,frame)]
        local_checks=0
        local_mismatch=0
        for strategy in ("early","confirmed"):
            for trade in case["reversal_backtest"][strategy]["trades"]:
                i=int(trade["entry_bar"])
                entry_ms=int(rows[i][0])
                if entry_ms<=cutoff:continue
                opportunities+=1
                if ORDER.index(frame)==len(ORDER)-1:
                    no_higher+=1
                    continue
                higher=ORDER[ORDER.index(frame)+1]
                hrows=histories[(symbol,higher)]
                # Signal is known at the close of the previous base candle.
                signal_close=int(rows[int(trade["signal_bar"])][0])+FRAME_MS[frame]
                if signal_close>entry_ms:raise AssertionError("signal after entry")
                idx=completed_higher_index(hrows,higher,signal_close)
                prefix=[r for r in hrows if int(r[0])+FRAME_MS[higher]<=signal_close]
                if idx+1!=len(prefix):
                    raise AssertionError("noncontiguous higher-timeframe history")
                for span in (20,50,200):
                    full=ema_at_closed_index(hrows,idx,span)
                    causal=ema_at_closed_index(prefix,len(prefix)-1,span)
                    checks+=1
                    local_checks+=1
                    if full is None or causal is None:
                        insufficient+=1
                        if full!=causal:
                            local_mismatch+=1
                            mismatches.append({"symbol":symbol,"frame":frame,"strategy":strategy,
                                               "entry_ms":entry_ms,"span":span,"type":"availability"})
                    elif abs(full-causal)>1e-10*max(1,abs(full)):
                        local_mismatch+=1
                        mismatches.append({"symbol":symbol,"frame":frame,"strategy":strategy,
                                           "entry_ms":entry_ms,"span":span,
                                           "full":full,"prefix":causal})
        by_market.append({"symbol":symbol,"timeframe":frame,
                          "checks":local_checks,"mismatches":local_mismatch})
    return {"status":"PASS" if not mismatches else "FAIL",
            "post_cutoff_opportunities":opportunities,"ema_value_checks":checks,
            "insufficient_history_checks":insufficient,
            "no_higher_frame_opportunities":no_higher,
            "mismatches":len(mismatches),"examples":mismatches[:10],
            "markets":by_market,
            "scope":"HTF EMA20/50/200 values at signal close, prior to entry",
            "warning":"NOT_PROSPECTIVE_PROFITABILITY; NOT_FULL_PORTFOLIO_FILTER"}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=audit(cases,histories)
    (folder/"bitget_htf_ema_prefix_audit.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("HTF EMA prefix audit:",json.dumps({k:v for k,v in result.items()
                                           if k not in ("markets","examples")}))
    for market in result["markets"]:
        print("HTF EMA market:",json.dumps(market))
    if result["status"]!="PASS":raise SystemExit("HTF EMA PREFIX MISMATCH")
if __name__=="__main__":main()
