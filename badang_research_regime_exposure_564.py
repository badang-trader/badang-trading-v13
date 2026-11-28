"""Count observable causal market-regime exposure by completed candle.

Warmup bars are unclassified, not assumed sideways. These counts do not
establish predictive validity or independent observations.
"""
from badang_research_regimes_555 import regime_at

def regime_exposure(candles,lookback=20,threshold=0.03):
    if not isinstance(lookback,int) or isinstance(lookback,bool) or lookback<1:
        raise ValueError("Invalid lookback")
    groups={"up":0,"down":0,"sideways":0}
    for index in range(lookback,len(candles)):
        groups[regime_at(candles,index,lookback,threshold)]+=1
    return {"regime_bars":groups,"unclassified_warmup_bars":min(lookback,len(candles)),
            "classified_bars":sum(groups.values()),
            "historical_observations_not_independent":True}
