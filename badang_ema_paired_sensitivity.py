"""Stage 87: paired same-timestamp EMA capital sensitivity, research only.

Uses existing prospective same-timeframe EMA eligibility; does not claim
prospective profitability, intrabar MDD, or exchange liquidation.
"""
import json
from pathlib import Path
from badang_prospective_ema_eligibility import audit
from badang_censored_equity_replay import replay
from badang_causal_mark_lookup import FRAME_MS

def run(cases,histories):
    report=audit(cases,histories)
    by_key={(c["symbol"],c["timeframe"]):c for c in cases}
    outputs=[]
    for strategy in ("early","confirmed"):
        selected=[t for r in report["results"] if r["strategy"]==strategy for t in r["sample_entries"]]
        modes={}
        for mode in ("ALL","EMA_ALIGNED"):
            events=[]
            for t in selected:
                if mode=="EMA_ALIGNED" and not t["ema_aligned"]:continue
                key=(t["symbol"],t["timeframe"])
                raw=by_key[key]["reversal_backtest"][strategy]["trades"][int(t["trade_id"].rsplit(":",1)[-1])]
                rows=histories[key]
                a,b=int(raw["entry_bar"]),int(raw["exit_bar"])
                reason="CLOSED" if raw["net_return"] is not None else raw["exit_reason"]
                e={"id":t["trade_id"],"symbol":key[0],"timeframe":key[1],
                   "side":t["side"],"entry_ts":int(rows[a][0]),
                   "entry_price":float(raw["entry"]),"reason":reason}
                if reason=="CLOSED":
                    e.update(exit_ts=int(rows[b][0])+FRAME_MS[key[1]],net_return=float(raw["net_return"]))
                if reason=="END_OF_PARTITION":
                    e["partition_end_ts"]=int(rows[b][0])+FRAME_MS[key[1]]
                events.append(e)
            modes[mode]=events
        relevant={(e["symbol"],e["timeframe"]) for events in modes.values() for e in events}
        # Same timeline for both arms; close observations are not forward-filled.
        times=sorted({int(r[0])+FRAME_MS[k[1]] for k in relevant for r in histories[k]
                      if int(r[0])>report["cutoff_ms"]})
        for lev in (1,2,3):
            for fraction in (.03,.05):
                for cap in (.20,.30):
                    arms={}
                    for mode,events in modes.items():
                        out=replay([{**e,"leverage":float(lev)} for e in events],
                                   histories,times,initial_capital=10000.,
                                   margin_fraction=fraction,max_margin_fraction=cap)
                        snaps={s["ts"]:s for s in out["snapshots"]}
                        arms[mode]={"snapshots":snaps,"rejected":len(out["rejected"]),
                                    "expired_partition_count":len(out["expired_partition_ids"]),
                                    "unclosed_count":len(out["unclosed_ids"])}
                    common=sorted(set(arms["ALL"]["snapshots"])&set(arms["EMA_ALIGNED"]["snapshots"]))
                    exact=[ts for ts in common if all(arms[m]["snapshots"][ts]["strict_observed_equity"] is not None
                                                       for m in arms)]
                    def metrics(mode):
                        arm=arms[mode];snaps=arm["snapshots"]
                        realized_peak=10000.;realized_mdd=0.
                        exact_peak=10000.;exact_mdd=0.
                        for s in snaps.values():
                            balance=10000.+s["realized_pnl"]
                            realized_peak=max(realized_peak,balance)
                            realized_mdd=max(realized_mdd,(realized_peak-balance)/realized_peak)
                        # Only common exact timestamps are comparable. Not intrabar MDD.
                        for ts in exact:
                            eq=snaps[ts]["strict_observed_equity"]
                            exact_peak=max(exact_peak,eq)
                            exact_mdd=max(exact_mdd,(exact_peak-eq)/exact_peak)
                        last=snaps[exact[-1]] if exact else None
                        return {"realized_mdd":realized_mdd,
                                "common_exact_close_mdd_lower_bound":exact_mdd,
                                "rejected":arm["rejected"],
                                "expired_partition_count":arm["expired_partition_count"],
                                "unclosed_count":arm["unclosed_count"],
                                "at_last_common_exact":({k:last[k] for k in (
                                    "ts","realized_pnl","observed_unrealized_pnl",
                                    "strict_observed_equity","reserved_margin",
                                    "available_capital_realized_basis","active_count")} if last else None)}
                    a,b=metrics("ALL"),metrics("EMA_ALIGNED")
                    outputs.append({"strategy":strategy,"leverage":lev,"margin_fraction":fraction,
                                    "max_margin_fraction":cap,"common_exact_observations":len(exact),
                                    "all":a,"ema":b,
                                    "ema_minus_all_equity":(
                                        b["at_last_common_exact"]["strict_observed_equity"]-
                                        a["at_last_common_exact"]["strict_observed_equity"] if exact else None)})
    return {"status":"RESEARCH_ONLY_NOT_INDEPENDENT_PROFITABILITY",
            "cutoff_ms":report["cutoff_ms"],"scenarios":outputs,
            "warnings":["SAME_TIMEFRAME_EMA_ONLY; HTF_FILTER_NOT_EVALUATED",
                        "COMMON_EXACT_CLOSE_MDD_IS_OBSERVATION_LOWER_BOUND",
                        "NO_INTRABAR_OR_EXCHANGE_LIQUIDATION_MODEL",
                        "HISTORICAL_SIGNAL_SELECTION_NOT_PROSPECTIVELY_VALIDATED"]}
def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=run(cases,histories)
    (folder/"bitget_ema_paired_sensitivity.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    for s in result["scenarios"]:
        print("paired EMA sensitivity:",json.dumps(s))
if __name__=="__main__":main()
