"""Validate historical research candle price fields before signal evaluation.

Open and close are required for fills; high and low must appear together if
supplied. Production market data supplies complete OHLC bars.
"""
import math

def validate_research_candles(candles):
    for index,bar in enumerate(candles):
        if not isinstance(bar,dict):
            raise ValueError("Invalid historical candle at index "+str(index))
        has_high="high" in bar
        has_low="low" in bar
        if has_high!=has_low:
            raise ValueError("Incomplete historical OHLC at index "+str(index))
        keys=("open","high","low","close") if has_high else ("open","close")
        try:
            values=[bar[key] for key in keys]
        except KeyError as exc:
            raise ValueError("Missing historical price at index "+str(index)) from exc
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in values):
            raise ValueError("Invalid historical price at index "+str(index))
        if has_high:
            op,hi,lo,cl=values
            if hi<max(op,cl,lo) or lo>min(op,cl,hi):
                raise ValueError("Inconsistent historical OHLC at index "+str(index))
    return True
