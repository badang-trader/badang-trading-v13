"""Research-only performance summary for chronological, closed trades.

Returns are unlevered fractions after fees/slippage, not equity PnL from live
orders. The caller must supply trades in chronological exit order.
"""
import math

def summarize_net_returns(returns):
    values=list(returns)
    if not values:
        raise ValueError("No completed trades")
    if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) or x<=-1 for x in values):
        raise ValueError("Invalid net trade return")
    equity=1.0
    peak=1.0
    max_drawdown=0.0
    wins=0
    gross_profit=0.0
    gross_loss=0.0
    for r in values:
        equity*=1+r
        if not math.isfinite(equity):
            raise ValueError("Equity arithmetic overflow")
        peak=max(peak,equity)
        max_drawdown=max(max_drawdown,1-equity/peak)
        if r>0:
            wins+=1
            gross_profit+=r
        elif r<0:
            gross_loss-=r
    profit_factor=(gross_profit/gross_loss if gross_loss>0 else None)
    return {"trades":len(values),"wins":wins,"win_rate":wins/len(values),
            "compounded_net_return":equity-1,
            "max_drawdown":max_drawdown,"profit_factor":profit_factor}
