"""Causal research-only fixed-horizon evaluation of precomputed trade signals.

No exchange orders. A signal generated at bar i enters at the *next* bar's
open, and exits at a later bar's close. Costs are explicit assumptions.
This is not a full strategy backtest or a profitability claim.
"""
import math
from badang_cost_model_544 import net_round_trip

def evaluate_signal(candles,signal_index,direction,horizon=4,fee_per_side=0.0006,slippage_per_side=0.0005):
    if not isinstance(signal_index,int) or isinstance(signal_index,bool) or signal_index<0:
        raise ValueError("Invalid signal index")
    if not isinstance(horizon,int) or isinstance(horizon,bool) or horizon<1:
        raise ValueError("Invalid horizon")
    if signal_index+1+horizon>=len(candles):
        raise ValueError("Insufficient future bars")
    # All bars are already closed in the supplied historical dataset.
    entry_index=signal_index+1
    exit_index=entry_index+horizon
    entry=float(candles[entry_index]["open"])
    exit_price=float(candles[exit_index]["close"])
    result=net_round_trip(entry,exit_price,direction,fee_per_side,slippage_per_side)
    return {"signal_index":signal_index,"entry_index":entry_index,
            "exit_index":exit_index,"direction":direction,**result}
