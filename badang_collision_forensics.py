"""Research-only forensic ledger for candles touching both stop and target.

Conservative stop-first accounting is verified against stored trades. This is
not tick-order reconstruction and cannot prove the actual exchange fill.
"""
import json
from pathlib import Path
from badang_execution_causal_audit import FEE,SLIPPAGE

def audit(cases,histories):
    collisions=[]
    for case in cases:
        symbol,frame=case["symbol"],case["timeframe"]
        rows=histories[(symbol,frame)]
        split=int(len(rows)*.7)
        for strategy in ("early","confirmed"):
            for idx,t in enumerate(case["reversal_backtest"][strategy]["trades"]):
                entry_bar=int(t["entry_bar"])
                limit=split if t["partition"]=="TRAIN" else len(rows)
                side=t["side"];stop=float(t["stop"]);target=float(t["target"])
                for bar in range(entry_bar,limit):
                    row=rows[bar]
                    hi,lo=float(row[2]),float(row[3])
                    sh=lo<=stop if side=="LONG" else hi>=stop
                    th=hi>=target if side=="LONG" else lo<=target
                    if sh and th:
                        op=float(row[1])
                        stop_fill=min(stop,op) if side=="LONG" else max(stop,op)
                        sign=1 if side=="LONG" else -1
                        net=sign*(stop_fill-float(t["entry"]))/float(t["entry"])-2*(FEE+SLIPPAGE)
                        collision={"trade_id":f"{strategy}:{t['partition']}:{symbol}:{frame}:{idx}",
                                   "side":side,"entry_ts_ms":int(rows[entry_bar][0]),
                                   "collision_ts_ms":int(row[0]),"stop":stop,"target":target,
                                   "stop_first_net_return":net,
                                   "recorded_exit_reason":t["exit_reason"],
                                   "recorded_exit_bar":int(t["exit_bar"]),
                                   "recorded_net_return":t["net_return"],
                                   "matches_stored":t["exit_reason"]=="STOP" and int(t["exit_bar"])==bar and
                                   t["net_return"] is not None and abs(net-float(t["net_return"]))<1e-10}
                        collisions.append(collision)
                    if sh or th:break
    mismatches=[x for x in collisions if not x["matches_stored"]]
    return {"status":"PASS" if not mismatches else "FAIL","collision_count":len(collisions),
            "mismatches":len(mismatches),"collisions":collisions,
            "warnings":["STOP_FIRST_CONSERVATIVE_ASSUMPTION",
                        "NO_TICK_PATH_OR_EXCHANGE_FILL_VERIFICATION",
                        "NO_LIQUIDATION_MODEL"]}
def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=audit(cases,histories)
    (folder/"bitget_collision_forensics.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("stop target collision forensics:",json.dumps(result))
    if result["status"]!="PASS":raise SystemExit("COLLISION FORENSICS MISMATCH")
if __name__=="__main__":main()
