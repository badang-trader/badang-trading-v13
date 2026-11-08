"""Research-only historical signal extraction from the real analysis engine.

Each signal is computed from a prefix ending at that completed candle.
No live orders, no current funding/OI projected backward into history.
"""
from badang_analysis_v13 import analyze
from badang_research_runner_548 import evaluate_signals

def research_engine_signals(candles,mode="scalp",warmup=205,end_index=None):
    if not isinstance(warmup,int) or isinstance(warmup,bool) or warmup<205:
        raise ValueError("Invalid warmup")
    if end_index is None:
        end_index=len(candles)
    if not isinstance(end_index,int) or isinstance(end_index,bool) or not 0<=end_index<=len(candles):
        raise ValueError("Invalid historical signal cutoff")
    signals=[]
    for i in range(warmup-1,end_index):
        result=analyze(candles[:i+1],mode=mode)
        if result.get("status")!="ok":
            raise ValueError("Historical analysis invalid at bar "+str(i))
        side=result.get("recommendation")
        if side in ("LONG","SHORT"):
            signals.append({"signal_index":i,"direction":side.lower()})
    return signals

def research_engine_backtest(candles,mode="scalp",horizon=4,fee_per_side=0.0006,slippage_per_side=0.0005):
    # Exclude signals whose full future exit window is unavailable.
    if not isinstance(horizon,int) or isinstance(horizon,bool) or horizon<1:
        raise ValueError("Invalid horizon")
    cutoff=len(candles)-horizon-1
    signals=research_engine_signals(candles,mode,end_index=cutoff)
    return evaluate_signals(candles,signals,horizon,fee_per_side,slippage_per_side)
