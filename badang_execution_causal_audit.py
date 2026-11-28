"""Stage 76: independent, chronological execution audit of reversal backtest.

Research-only. Replays each stored trade from its entry forward, one candle
at a time. This checks execution arithmetic, not independent signal selection.
"""
import json
from pathlib import Path

FEE=0.0006
SLIPPAGE=0.0003

def audit_case(case,rows):
    issues=[]
    trades_checked=0
    candles_checked=0
    stop_target_collisions=0
    gap_stop_fills=0
    partition_end_checks=0
    split=int(len(rows)*0.7)
    for strategy in ("early","confirmed"):
        trades=case["reversal_backtest"][strategy]["trades"]
        for index,t in enumerate(trades):
            trades_checked+=1
            signal=int(t["signal_bar"])
            entry_bar=int(t["entry_bar"])
            end_bar=int(t["exit_bar"])
            partition=t["partition"]
            end=split if partition=="TRAIN" else len(rows)
            if entry_bar!=signal+1 or not (0<=signal<entry_bar<end<=len(rows)):
                issues.append({"strategy":strategy,"index":index,"error":"ENTRY_OR_PARTITION"})
                continue
            entry=float(rows[entry_bar][1])
            side=t["side"]
            stop=float(t["stop"])
            target=float(t["target"])
            risk=entry-stop if side=="LONG" else stop-entry
            expected_target=entry+2*risk if side=="LONG" else entry-2*risk
            if risk<=0 or abs(target-expected_target)>1e-9*max(1,abs(target)):
                issues.append({"strategy":strategy,"index":index,"error":"RISK_OR_TARGET"})
                continue
            reason="END_OF_PARTITION" if partition=="TRAIN" else "END_OF_DATA"
            observed_exit=end-1
            exit_price=None
            for k in range(entry_bar,end):
                candles_checked+=1
                op,hi,lo=(float(rows[k][j]) for j in (1,2,3))
                stop_hit=lo<=stop if side=="LONG" else hi>=stop
                target_hit=hi>=target if side=="LONG" else lo<=target
                if stop_hit and target_hit:stop_target_collisions+=1
                if stop_hit:
                    reason="STOP"
                    observed_exit=k
                    exit_price=min(stop,op) if side=="LONG" else max(stop,op)
                    if exit_price!=stop:gap_stop_fills+=1
                    break
                if target_hit:
                    reason="TARGET"
                    observed_exit=k
                    exit_price=target
                    break
            if exit_price is None:partition_end_checks+=1
            sign=1 if side=="LONG" else -1
            net=(sign*(exit_price-entry)/entry-2*(FEE+SLIPPAGE)
                 if exit_price is not None else None)
            if (reason!=t["exit_reason"] or observed_exit!=end_bar
                or abs(entry-float(t["entry"]))>1e-9*max(1,abs(entry))
                or ((net is None)!=(t["net_return"] is None))
                or (net is not None and abs(net-float(t["net_return"]))>1e-10)):
                issues.append({"strategy":strategy,"index":index,
                               "error":"EXIT_OR_NET_MISMATCH",
                               "expected_reason":reason,"recorded_reason":t["exit_reason"],
                               "expected_exit_bar":observed_exit,"recorded_exit_bar":end_bar})
    return {"symbol":case["symbol"],"timeframe":case["timeframe"],
            "trades_checked":trades_checked,"chronological_candle_checks":candles_checked,
            "stop_target_collisions":stop_target_collisions,
            "gap_stop_fills":gap_stop_fills,
            "censored_end_checks":partition_end_checks,
            "mismatches":len(issues),"examples":issues[:10]}

def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    markets=[]
    for case in cases:
        symbol,frame=case["symbol"],case["timeframe"]
        rows=json.loads((folder/f"bitget_{symbol}_{frame}.json").read_text(encoding="utf-8"))["candles"]
        markets.append(audit_case(case,rows))
    fields=("trades_checked","chronological_candle_checks","stop_target_collisions",
            "gap_stop_fills","censored_end_checks","mismatches")
    totals={k:sum(m[k] for m in markets) for k in fields}
    report={"status":"PASS" if not totals["mismatches"] else "FAIL",
            "totals":totals,"markets":markets,
            "limitations":["EXECUTION_REPLAY_ONLY","SIGNAL_SELECTION_NOT_INDEPENDENT",
                           "NO_EXCHANGE_MARK_OR_LIQUIDATION_MODEL",
                           "HTF_EMA_NOT_AUDITED","NO_PROSPECTIVE_PROFITABILITY_CLAIM"]}
    (folder/"bitget_execution_causal_audit.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("execution causal audit:",json.dumps({"status":report["status"],**totals}))
    for m in markets:
        print("execution causal market:",json.dumps({k:v for k,v in m.items() if k!="examples"}))
    if report["status"]!="PASS":raise SystemExit("EXECUTION CAUSAL AUDIT FAILED")
if __name__=="__main__":main()
