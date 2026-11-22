"""Research-only paired EMA equity replay on post-cutoff historical candidates.

Uses identical candidate universe and capital settings, and preserves censored
positions. This is a diagnostic, NOT an independent prospective profit claim.
"""
import json
from pathlib import Path
from badang_prospective_ema_eligibility import audit
from badang_censored_equity_replay import replay
from badang_causal_mark_lookup import FRAME_MS

def summarize(out, initial=10000.0):
    snapshots=out["snapshots"]
    peak=initial
    realized_dd=0.0
    observed_peak=initial
    observed_dd=0.0
    for row in snapshots:
        balance=initial+row["realized_pnl"]
        peak=max(peak,balance)
        realized_dd=max(realized_dd,(peak-balance)/peak)
        equity=row["strict_observed_equity"]
        if equity is not None:
            observed_peak=max(observed_peak,equity)
            observed_dd=max(observed_dd,(observed_peak-equity)/observed_peak)
    exact=[s for s in snapshots if s["strict_observed_equity"] is not None]
    final=snapshots[-1] if snapshots else None
    return {"accepted":len(out["accepted_ids"]) if "accepted_ids" in out else None,
            "rejected":len(out["rejected"]),
            "rejected_ids":[r["id"] for r in out["rejected"]],
            "unclosed_ids":out["unclosed_ids"],
            "realized_pnl":final["realized_pnl"] if final else 0,
            "final_reserved_margin":final["reserved_margin"] if final else 0,
            "final_available_capital":final["available_capital_realized_basis"] if final else initial,
            "final_unrealized_pnl":final["observed_unrealized_pnl"] if final else 0,
            "realized_mdd":realized_dd,
            "exact_close_mdd_lower_bound":observed_dd,
            "last_exact_observation":({k:exact[-1][k] for k in
                 ("ts","strict_observed_equity","observed_unrealized_pnl",
                  "reserved_margin","active_count")} if exact else None),
            "nonexact_snapshots":sum(bool(s["non_exact_marks"]) for s in snapshots),
            "missing_snapshots":sum(bool(s["missing_marks"]) for s in snapshots)}

def run(cases,histories):
    report=audit(cases,histories)
    by_key={(c["symbol"],c["timeframe"]):c for c in cases}
    results=[]
    for strategy in ("early","confirmed"):
        selected=[t for r in report["results"] if r["strategy"]==strategy
                  for t in r["sample_entries"]]
        for mode in ("ALL","EMA_ALIGNED"):
            events=[]
            for t in selected:
                if mode=="EMA_ALIGNED" and not t["ema_aligned"]:
                    continue
                key=(t["symbol"],t["timeframe"])
                case=by_key[key]
                index=int(t["trade_id"].rsplit(":",1)[-1])
                raw=case["reversal_backtest"][strategy]["trades"][index]
                rows=histories[key]
                a,b=int(raw["entry_bar"]),int(raw["exit_bar"])
                reason="CLOSED" if raw["net_return"] is not None else raw["exit_reason"]
                if reason not in ("CLOSED","END_OF_DATA","END_OF_PARTITION"):
                    raise ValueError("invalid reason")
                event={"id":t["trade_id"],"symbol":key[0],"timeframe":key[1],
                       "side":t["side"],"entry_ts":int(rows[a][0]),
                       "entry_price":float(raw["entry"]),"leverage":2.,
                       "reason":reason}
                if reason=="CLOSED":
                    event["exit_ts"]=int(rows[b][0])+FRAME_MS[key[1]]
                    event["net_return"]=float(raw["net_return"])
                if reason=="END_OF_PARTITION":
                    event["partition_end_ts"]=int(rows[b][0])+FRAME_MS[key[1]]
                events.append(event)
            relevant={(e["symbol"],e["timeframe"]) for e in events}
            cutoff=report["cutoff_ms"]
            times=sorted({int(r[0])+FRAME_MS[k[1]] for k in relevant
                          for r in histories[k] if int(r[0])>cutoff})
            result=replay(events,histories,times,initial_capital=10000.,
                          margin_fraction=.05,max_margin_fraction=.30)
            summary=summarize(result)
            summary["accepted"]=len(events)-summary["rejected"]
            results.append({"strategy":strategy,"mode":mode,"candidates":len(events),
                            "candidate_censored":sum(e["reason"]!="CLOSED" for e in events),
                            **summary})
    return {"status":"RESEARCH_ONLY_PAIRED_EMA_EQUITY_DIAGNOSTIC",
            "cutoff_ms":report["cutoff_ms"],"results":results,
            "warnings":["NOT_PROSPECTIVE_OUTCOME_VALIDATED",
                        "HTF_FILTER_NOT_EVALUATED",
                        "CLOSED_CANDLE_NOT_EXCHANGE_MARK",
                        "NO_INTRABAR_LIQUIDATION_MODEL",
                        "CANDIDATE_GENERATION_MAY_HAVE_LOOKAHEAD"]}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    report=run(cases,histories)
    (folder/"bitget_paired_ema_equity.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for row in report["results"]:
        print("paired EMA equity:",json.dumps(row))
    print("prospective EMA performance: NOT_ESTABLISHED")
if __name__=="__main__":
    main()
