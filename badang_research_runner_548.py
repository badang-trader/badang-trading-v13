"""Chronological, research-only evaluation of externally generated signals.

Signals must be emitted from historical information available at their bar.
One position at a time; conflicting signals while a trade is open are skipped.
No live exchange connectivity or order execution.
"""
from badang_research_backtest_545 import evaluate_signal
from badang_research_ledger_547 import summarize_nonoverlapping_trades
from badang_research_candle_validation_568 import validate_research_candles

def evaluate_signals(candles,signals,horizon=4,fee_per_side=0.0006,slippage_per_side=0.0005):
    validate_research_candles(candles)
    trades=[]
    skipped=0
    previous_signal=-1
    previous_exit=-1
    for signal in signals:
        if not isinstance(signal,dict):
            raise ValueError("Invalid signal")
        i=signal.get("signal_index")
        direction=signal.get("direction")
        if not isinstance(i,int) or isinstance(i,bool) or i<=previous_signal:
            raise ValueError("Signals must be strictly chronological")
        previous_signal=i
        if i<=previous_exit:
            skipped+=1
            continue
        trade=evaluate_signal(candles,i,direction,horizon,fee_per_side,slippage_per_side)
        trades.append(trade)
        previous_exit=trade["exit_index"]
    return {"trades":trades,"skipped_overlaps":skipped,
            "summary":summarize_nonoverlapping_trades(trades) if trades else None}
