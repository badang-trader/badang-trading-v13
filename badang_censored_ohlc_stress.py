"""Stage 92: conservative OHLC adverse excursion for open/censored trades.

This is a per-position stress diagnostic, NOT synchronized account MDD,
mark-price liquidation or an executable fill reconstruction.
"""
import json
from pathlib import Path
from badang_prospective_ema_eligibility import audit as ema_audit

def audit(cases,histories):
    eligibility=ema_audit(cases,histories)
    by_key={(c["symbol"],c["timeframe"]):c for c in cases}
    results=[]
    for market in eligibility["results"]:
        key=(market["symbol"],market["timeframe"])
        rows=histories[key]
        for t in market["sample_entries"]:
            raw=by_key[key]["reversal_backtest"][market["strategy"]]["trades"][int(t["trade_id"].rsplit(":",1)[-1])]
            if raw["net_return"] is not None:continue
            start,end=int(raw["entry_bar"]),int(raw["exit_bar"])
            if not 0<=start<=end<len(rows):
                raise AssertionError("invalid censored trade bars")
            entry=float(raw["entry"])
            side=t["side"]
            observations=[]
            for i in range(start,end+1):
                candle=rows[i]
                high,low,close=float(candle[2]),float(candle[3]),float(candle[4])
                if not 0<low<=high or not low<=close<=high:
                    raise AssertionError("invalid OHLC")
                adverse=low if side=="LONG" else high
                direction=1 if side=="LONG" else -1
                adverse_return=direction*(adverse/entry-1)
                close_return=direction*(close/entry-1)
                observations.append({"ts":int(candle[0]),"adverse_return":adverse_return,
                                     "close_return":close_return})
            worst=min(observations,key=lambda x:x["adverse_return"])
            final=observations[-1]
            results.append({"trade_id":t["trade_id"],"strategy":market["strategy"],
                            "symbol":key[0],"timeframe":key[1],"side":side,
                            "entry_ts":int(rows[start][0]),"censored_reason":raw["exit_reason"],
                            "observed_candle_count":len(observations),
                            "worst_ohlc_adverse_return":worst["adverse_return"],
                            "worst_ohlc_bar_ts":worst["ts"],
                            "last_close_return":final["close_return"],
                            "last_candle_adverse_return":final["adverse_return"],
                            "warnings":["OHLC_HIGH_LOW_ORDER_UNKNOWN",
                                        "NOT_EXECUTED_PNL_OR_EXCHANGE_MARK",
                                        "NOT_SYNCHRONIZED_ACCOUNT_MDD"]})
    return {"status":"PASS","cutoff_ms":eligibility["cutoff_ms"],
            "censored_post_cutoff_count":len(results),
            "results":results,
            "scope":"POST_CUTOFF_CENSORED_PER_POSITION_OHLC_STRESS_ONLY",
            "no_liquidation_model":True,"no_account_level_intrabar_mdd":True}
def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=audit(cases,histories)
    (folder/"bitget_censored_ohlc_stress.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("censored OHLC stress:",json.dumps(
        {k:v for k,v in result.items() if k!="results"}))
if __name__=="__main__":main()
