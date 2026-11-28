"""Research-only execution cost sensitivity; no live trading.

Reprices completed trades with the same historical entry and exit prices.
Scenarios are assumptions, not realized exchange fill estimates.
"""
from badang_cost_model_544 import net_round_trip
from badang_research_metrics_546 import summarize_net_returns

def cost_sensitivity(trades,scenarios=None):
    if scenarios is None:
        scenarios={"baseline":(.0006,.0005),"elevated":(.001,.0015),"stress":(.002,.003)}
    records=list(trades)
    if not isinstance(scenarios,dict) or not scenarios:
        raise ValueError("Missing cost scenarios")
    results={}
    zero_cost_returns=[]
    for trade in records:
        if not isinstance(trade,dict):
            raise ValueError("Invalid trade")
        zero_cost_returns.append(net_round_trip(trade["raw_entry"],trade["raw_exit"],trade["direction"],0,0)["net_return"])
    for name,costs in scenarios.items():
        if not isinstance(name,str) or not name or not isinstance(costs,(tuple,list)) or len(costs)!=2:
            raise ValueError("Invalid cost scenario")
        fee,slippage=costs
        returns=[]
        for trade in records:
            if not isinstance(trade,dict):
                raise ValueError("Invalid trade")
            result=net_round_trip(trade["raw_entry"],trade["raw_exit"],trade["direction"],fee,slippage)
            returns.append(result["net_return"])
        results[name]={"fee_per_side":fee,"slippage_per_side":slippage,
                       "gross_winners_turning_nonpositive":sum(g>0 and n<=0 for g,n in zip(zero_cost_returns,returns)),
                       "net_winning_trades":sum(n>0 for n in returns),
                       "metrics":summarize_net_returns(returns) if returns else None}
    return {"read_only":True,"scenario_assumptions_not_realized_fills":True,"scenarios":results}
