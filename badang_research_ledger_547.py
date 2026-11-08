"""Research-only sequential trade ledger: reject overlapping positions.

Only closed trades, chronological bars and explicit net returns are accepted.
This models one position at a time, not a leveraged live trading account.
"""
from badang_research_metrics_546 import summarize_net_returns

def summarize_nonoverlapping_trades(trades):
    records=list(trades)
    if not records:
        raise ValueError("No completed trades")
    previous_exit=-1
    returns=[]
    for trade in records:
        if not isinstance(trade,dict):
            raise ValueError("Invalid trade record")
        start=trade.get("entry_index")
        end=trade.get("exit_index")
        if (not isinstance(start,int) or isinstance(start,bool) or
            not isinstance(end,int) or isinstance(end,bool) or
            start<0 or end<=start):
            raise ValueError("Invalid trade timing")
        if start<=previous_exit:
            raise ValueError("Overlapping or unsorted trades")
        if "net_return" not in trade:
            raise ValueError("Missing net return")
        returns.append(trade["net_return"])
        previous_exit=end
    return summarize_net_returns(returns)
