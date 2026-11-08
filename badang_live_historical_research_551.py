"""Bounded live public Bitget historical research check; no orders.

Only the exchange's confirmed candles are used. Reports results without
asserting profitability. Live API failures fail this validation step.
"""
import json
from bitget_market_data import fastest_candles
from badang_engine_research_549 import research_engine_backtest

def main():
    reports=[]
    for symbol,frame,mode in (("BTCUSDT","15m","scalp"),("ETHUSDT","1D","swing")):
        snapshot=fastest_candles(symbol,frame)
        # Bitget returns [timestamp,open,high,low,close,volume] string rows.\n        # The analysis engine accepts them, but the research execution ledger\n        # requires named OHLC fields for next-open and exit-close pricing.\n        closed=[{"timestamp":row[0],"open":float(row[1]),\n                 "high":float(row[2]),"low":float(row[3]),\n                 "close":float(row[4]),"volume":float(row[5])}\n                for row in snapshot["candles"][:-1]]
        if len(closed)<210:
            raise ValueError("Too few confirmed historical bars: "+symbol+" "+frame)
        result=research_engine_backtest(closed,mode=mode,horizon=3)
        metrics=result["summary"]
        reports.append({"symbol":symbol,"frame":frame,"mode":mode,
                        "confirmed_bars":len(closed),
                        "trades":len(result["trades"]),
                        "skipped_overlaps":result["skipped_overlaps"],
                        "win_rate":metrics["win_rate"] if metrics else None,
                        "compounded_net_return":metrics["compounded_net_return"] if metrics else None,
                        "max_drawdown":metrics["max_drawdown"] if metrics else None,
                        "fee_per_side_assumed":0.0006,
                        "slippage_per_side_assumed":0.0005})
    print("LIVE_HISTORICAL_RESEARCH_SUMMARY "+json.dumps(
        {"read_only":True,"trading_enabled":False,"results":reports},allow_nan=False))
if __name__=="__main__":
    main()
