"""Causal research market regime labels using only signal-time history.

Regimes use the trailing close return over a fixed lookback, not future
performance. Thresholds are exploratory and not a predictive guarantee.
"""
import math

def regime_at(candles,signal_index,lookback=20,threshold=0.03):
    if not isinstance(signal_index,int) or isinstance(signal_index,bool) or signal_index<0:
        raise ValueError("Invalid signal index")
    if not isinstance(lookback,int) or isinstance(lookback,bool) or lookback<1:
        raise ValueError("Invalid lookback")
    if not isinstance(threshold,(int,float)) or isinstance(threshold,bool) or not math.isfinite(threshold) or threshold<=0:
        raise ValueError("Invalid threshold")
    if signal_index>=len(candles) or signal_index<lookback:
        raise ValueError("Insufficient prior candles")
    earlier=float(candles[signal_index-lookback]["close"])
    current=float(candles[signal_index]["close"])
    if not math.isfinite(earlier) or not math.isfinite(current) or earlier<=0 or current<=0:
        raise ValueError("Invalid close")
    change=current/earlier-1
    if not math.isfinite(change):
        raise ValueError("Invalid return")
    return "up" if change>=threshold else "down" if change<=-threshold else "sideways"
