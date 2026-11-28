"""Offline Bitget candidate-to-equity adapter. No orders or exchange mark prices.

Each strategy/partition is an independent hypothetical account. The existing
70/30 per-timeframe split is NOT a prospective nonoverlapping holdout.
"""
import json
from collections import Counter
from pathlib import Path
from badang_censored_equity_replay import replay
from badang_causal_mark_lookup import FRAME_MS

def build_events(cases,histories,strategy,partition,leverage=2.0):
    events=[]
    for case in cases:
        key=(case["symbol"],case["timeframe"])
        rows=histories[key]
        trades=case["reversal_backtest"][strategy]["trades"]
        for i,t in enumerate(trades):
            if t["partition"]!=partition:continue
            a,b=t["entry_bar"],t["exit_bar"]
            if not 0<=a<=b<len(rows):raise ValueError("invalid trade bars")
            reason=("CLOSED" if t["net_return"] is not None else t["exit_reason"])
            if reason not in ("CLOSED","END_OF_PARTITION","END_OF_DATA"):
                raise ValueError("unknown censored reason")
            e=dict(id=f"{strategy}:{partition}:{key[0]}:{key[1]}:{i}",
                   symbol=key[0],timeframe=key[1],side=t["side"],
                   entry_ts=int(rows[a][0]),entry_price=float(t["entry"]),
                   leverage=leverage,reason=reason)
            if reason=="CLOSED":
                e["exit_ts"]=int(rows[b][0])+FRAME_MS[key[1]]
                e["net_return"]=float(t["net_return"])
            elif reason=="END_OF_PARTITION":
                e["partition_end_ts"]=int(rows[b][0])+FRAME_MS[key[1]]
            events.append(e)
    return events

def run_scenario(cases,histories,strategy,partition,*,initial_capital=10000,
                 margin_fraction=.05,max_margin_fraction=.30,leverage=2):
    events=build_events(cases,histories,strategy,partition,leverage)
    relevant={(e["symbol"],e["timeframe"]) for e in events}
    timestamps=sorted({int(r[0])+FRAME_MS[k[1]] for k in relevant
                       for r in histories[k]})
    out=replay(events,histories,timestamps,initial_capital=initial_capital,
               margin_fraction=margin_fraction,max_margin_fraction=max_margin_fraction)
    snapshots=out["snapshots"]
    realized_peak=initial_capital
    observed_peak=initial_capital
    realized_dd=observed_dd=0.
    exact_count=0
    for s in snapshots:
        capital=initial_capital+s["realized_pnl"]
        realized_peak=max(realized_peak,capital)
        realized_dd=max(realized_dd,(realized_peak-capital)/realized_peak)
        equity=s["strict_observed_equity"]
        if equity is not None:
            exact_count+=1
            observed_peak=max(observed_peak,equity)
            observed_dd=max(observed_dd,(observed_peak-equity)/observed_peak)
    exact_rows=[row for row in snapshots if row["strict_observed_equity"] is not None]
    last_exact=exact_rows[-1] if exact_rows else None
    missing_count=sum(bool(row["missing_marks"]) for row in snapshots)
    nonexact_count=sum(bool(row["non_exact_marks"]) for row in snapshots)
    counts=Counter(e["reason"] for e in events)
    return {"strategy":strategy,"partition":partition,"leverage":leverage,"margin_fraction":margin_fraction,"max_margin_fraction":max_margin_fraction,"event_counts":dict(counts),
            "total_candidates":len(events),"accepted":len(events)-len(out["rejected"]),
            "rejected":len(out["rejected"]),"realized_pnl":snapshots[-1]["realized_pnl"] if snapshots else 0.,
            "final_reserved_margin":snapshots[-1]["reserved_margin"] if snapshots else 0.,
            "final_available_capital_realized_basis":snapshots[-1]["available_capital_realized_basis"] if snapshots else initial_capital,
            "final_observed_unrealized_pnl":snapshots[-1]["observed_unrealized_pnl"] if snapshots else 0.,
            "realized_drawdown":realized_dd,
            "exact_close_observed_drawdown_lower_bound":observed_dd,
            "exact_snapshots":exact_count,"snapshots":len(snapshots),
            "missing_price_snapshots":missing_count,
            "non_exact_price_snapshots":nonexact_count,
            "max_reserved_margin":max((row["reserved_margin"] for row in snapshots),default=0.),
            "last_exact_common_observation":({
                "ts":last_exact["ts"],
                "strict_observed_equity":last_exact["strict_observed_equity"],
                "observed_unrealized_pnl":last_exact["observed_unrealized_pnl"],
                "reserved_margin":last_exact["reserved_margin"],
                "active_count":last_exact["active_count"]}
                if last_exact is not None else None),
            "unclosed_ids":out["unclosed_ids"],
            "expired_partition_ids":out["expired_partition_ids"],
            "warnings":["EXACT_CLOSE_DRAWDOWN_IS_NOT_INTRABAR_OR_EXCHANGE_MARK_DRAWDOWN",
                        "NOT_PROSPECTIVE_HOLDOUT","NO_LIQUIDATION_MODEL",
                        "NO_INDEPENDENT_EMA_PERFORMANCE_CLAIM"]}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    results=[run_scenario(cases,histories,strategy,partition)
             for strategy in ("early","confirmed") for partition in ("TRAIN","HOLDOUT")]
    sensitivity=[run_scenario(cases,histories,strategy,"HOLDOUT",
                    leverage=lev,margin_fraction=margin,max_margin_fraction=limit)
                 for strategy in ("early","confirmed")
                 for lev,margin,limit in ((1,.05,.30),(2,.05,.30),
                                          (3,.05,.30),(2,.03,.30),
                                          (2,.05,.20))]
    output={"status":"RESEARCH_ONLY_CENSORED_EQUITY_OBSERVED_CLOSE",
            "source":"BITGET_PUBLIC_HISTORY_API","results":results,"sensitivity":sensitivity}
    (folder/"bitget_censored_equity_replay.json").write_text(
        json.dumps(output,indent=2,ensure_ascii=False),encoding="utf-8")
    print("censored equity scenarios:",len(results))
    print("sensitivity scenarios:",len(sensitivity))
    for r in sensitivity:
        print("sensitivity:",json.dumps({k:r[k] for k in
              ("strategy","leverage","margin_fraction","max_margin_fraction",
               "accepted","rejected","realized_pnl","realized_drawdown",
               "max_reserved_margin")}))
    for r in results:
        print(json.dumps({k:v for k,v in r.items() if k not in ("unclosed_ids","expired_partition_ids")}))
if __name__=="__main__":main()
