"""Conservative sample adequacy flags for research backtests.

No win-rate or profit claims when completed trades are sparse.
These are screening thresholds, not statistical proof of profitability.
"""
def assess_sample(completed_trades,confirmed_bars,minimum_trades=30,minimum_bars=1000):
    for name,value in (("completed_trades",completed_trades),
                       ("confirmed_bars",confirmed_bars),
                       ("minimum_trades",minimum_trades),
                       ("minimum_bars",minimum_bars)):
        if not isinstance(value,int) or isinstance(value,bool) or value<0:
            raise ValueError("Invalid "+name)
    if minimum_trades<1 or minimum_bars<1:
        raise ValueError("Minimum thresholds must be positive")
    reasons=[]
    if completed_trades<minimum_trades:
        reasons.append("INSUFFICIENT_COMPLETED_TRADES")
    if confirmed_bars<minimum_bars:
        reasons.append("INSUFFICIENT_HISTORICAL_BARS")
    return {"sample_adequate_for_preliminary_review":not reasons,
            "profitability_verified":False,
            "completed_trades":completed_trades,
            "confirmed_bars":confirmed_bars,
            "minimum_trades":minimum_trades,
            "minimum_bars":minimum_bars,
            "warnings":reasons}
