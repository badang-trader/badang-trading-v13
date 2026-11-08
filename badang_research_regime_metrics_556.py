"""Conditional research trade performance by causal signal-time regime.

Grouped compounded returns are diagnostic only, NOT portfolio equity curves.
"""
from badang_research_regimes_555 import regime_at
from badang_research_metrics_546 import summarize_net_returns
from badang_research_ledger_547 import summarize_nonoverlapping_trades

def summarize_by_regime(candles,trades,lookback=20,threshold=0.03):
    records=list(trades)
    if records:
        summarize_nonoverlapping_trades(records)
    groups={"up":[],"down":[],"sideways":[]}
    for trade in records:
        if not isinstance(trade,dict) or "signal_index" not in trade or "net_return" not in trade:
            raise ValueError("Invalid completed trade")
        label=regime_at(candles,trade["signal_index"],lookback,threshold)
        groups[label].append(trade["net_return"])
    return {label:{"trade_count":len(values),
                   "conditional_only_not_portfolio":True,
                   "metrics":summarize_net_returns(values) if values else None}
            for label,values in groups.items()}
