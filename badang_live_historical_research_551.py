"""Bounded live public Bitget historical research check; no orders.

Only the exchange's confirmed candles are used. Reports results without
asserting profitability. Live API failures fail this validation step.
"""
import json
from bitget_market_data import fastest_candles
from badang_engine_research_549 import research_engine_backtest
from badang_research_sample_554 import assess_sample
from badang_research_regime_metrics_556 import summarize_by_regime
from badang_research_cost_sensitivity_560 import cost_sensitivity

def convert_closed_candles(snapshot):
    """Convert confirmed Bitget rows to named OHLCV values."""
    return [{"timestamp":row[0],"open":float(row[1]),
             "high":float(row[2]),"low":float(row[3]),
             "close":float(row[4]),"volume":float(row[5])}
            for row in snapshot["candles"][:-1]]

def main():
    reports=[]
    for symbol,frame,mode in (("BTCUSDT","15m","scalp"),("ETHUSDT","1D","swing")):
        snapshot=fastest_candles(symbol,frame)
        closed=convert_closed_candles(snapshot)
        if len(closed)<210:
            raise ValueError("Too few confirmed historical bars: "+symbol+" "+frame)
        result=research_engine_backtest(closed,mode=mode,horizon=3)
        metrics=result["summary"]
        reports.append({"symbol":symbol,"frame":frame,"mode":mode,
                        "confirmed_bars":len(closed),
                        "trades":len(result["trades"]),
                        "skipped_overlaps":result["skipped_overlaps"],
                        "conditional_regime_metrics":summarize_by_regime(closed,result["trades"]),
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
