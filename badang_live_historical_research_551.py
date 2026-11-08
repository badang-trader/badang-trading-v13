"""Bounded live public Bitget historical research check; no orders.

Only the exchange's confirmed candles are used. Reports results without
asserting profitability. Live API failures fail this validation step.
"""
import json
import math
import re
from bitget_market_data import fastest_candles
from badang_engine_research_549 import research_engine_backtest
from badang_research_sample_554 import assess_sample
from badang_research_regime_metrics_556 import summarize_by_regime
from badang_research_cost_sensitivity_560 import cost_sensitivity
from badang_research_regime_sample_563 import regime_sample_review
from badang_research_regime_exposure_564 import regime_exposure
from badang_research_timestamp_validation_569 import validate_research_timestamps

def parse_exchange_timestamp(value):
    """Require exchange epoch milliseconds, never silently coerce seconds."""
    if isinstance(value,bool) or not (
        isinstance(value,int) or (isinstance(value,str) and re.fullmatch(r"[0-9]{13}",value))
    ):
        raise ValueError("Invalid exchange millisecond timestamp")
    timestamp=int(value)
    if not 10**12<=timestamp<10**14:
        raise ValueError("Exchange timestamp must be epoch milliseconds")
    return timestamp

def _exchange_number(value,field,allow_zero=False):
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):
        raise ValueError("Invalid exchange "+field)
    if isinstance(value,str) and not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)",value):
        raise ValueError("Invalid exchange "+field)
    number=float(value)
    if not math.isfinite(number) or number<0 or (number==0 and not allow_zero):
        raise ValueError("Invalid exchange "+field)
    return number

def convert_closed_candles(snapshot):
    """Validate and convert confirmed Bitget rows; exclude newest open bar."""
    if not isinstance(snapshot,dict) or not isinstance(snapshot.get("candles"),list):
        raise ValueError("Invalid exchange candle snapshot")
    if len(snapshot["candles"])<2:
        raise ValueError("Insufficient exchange candles to confirm a closed bar")
    rows=[]
    for row in snapshot["candles"][:-1]:
        if not isinstance(row,(list,tuple)) or len(row)<6:
            raise ValueError("Invalid exchange OHLCV row")
        op=_exchange_number(row[1],"open")
        hi=_exchange_number(row[2],"high")
        lo=_exchange_number(row[3],"low")
        cl=_exchange_number(row[4],"close")
        vol=_exchange_number(row[5],"volume",allow_zero=True)
        if hi<max(op,lo,cl) or lo>min(op,hi,cl):
            raise ValueError("Inconsistent exchange OHLC")
        rows.append({"timestamp":parse_exchange_timestamp(row[0]),
                     "open":op,"high":hi,"low":lo,"close":cl,"volume":vol})
    return rows

def main():
    reports=[]
    for symbol,frame,mode in (("BTCUSDT","15m","scalp"),("ETHUSDT","1D","swing")):
        snapshot=fastest_candles(symbol,frame)
        closed=convert_closed_candles(snapshot)
        validate_research_timestamps(closed,{"15m":900000,"1D":86400000}[frame])
        if len(closed)<210:
            raise ValueError("Too few confirmed historical bars: "+symbol+" "+frame)
        result=research_engine_backtest(closed,mode=mode,horizon=3)
        metrics=result["summary"]
        reports.append({"symbol":symbol,"frame":frame,"mode":mode,
                        "confirmed_bars":len(closed),
                        "trades":len(result["trades"]),
                        "skipped_overlaps":result["skipped_overlaps"],
                        "conditional_regime_metrics":summarize_by_regime(closed,result["trades"]),
                        "regime_sample_review":regime_sample_review(closed,result["trades"]),
                        "regime_exposure":regime_exposure(closed),
                        "execution_cost_sensitivity":cost_sensitivity(result["trades"]),
                        "sample_assessment":assess_sample(len(result["trades"]),len(closed)),
                        "win_rate":metrics["win_rate"] if metrics else None,
                        "compounded_net_return":metrics["compounded_net_return"] if metrics else None,
                        "max_drawdown":metrics["max_drawdown"] if metrics else None,
                        "fee_per_side_assumed":0.0006,
                        "slippage_per_side_assumed":0.0005})
    print("LIVE_HISTORICAL_RESEARCH_SUMMARY "+json.dumps(
        {"read_only":True,"trading_enabled":False,"results":reports},allow_nan=False))
if __name__=="__main__":
    main()
