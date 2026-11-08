"""Research backtests must not silently accept corrupt candle sequences.

Validation is deliberately limited to the OHLC fields used for fill pricing.
"""
import math

def validate_research_candles(candles):
    for index,bar in enumerate(candles):
        if not isinstance(bar,dict):
            raise ValueError("Invalid historical candle at index "+str(index))
        try:
            values=[bar[key] for key in ("open","high","low","close")]
        except KeyError as exc:
            raise ValueError("Missing historical OHLC at index "+str(index)) from exc
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in values):
            raise ValueError("Invalid historical OHLC at index "+str(index))
        op,hi,lo,cl=values
        if hi<max(op,cl,lo) or lo>min(op,cl,hi):
            raise ValueError("Inconsistent historical OHLC at index "+str(index))
    return True
