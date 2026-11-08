"""Research-only, fee-aware round-trip return accounting.

This module does not generate signals, connect to exchanges, or place orders.
All fee and slippage assumptions are explicit fractions of notional per side.
"""
import math

def net_round_trip(entry,exit_price,direction,fee_per_side=0.0006,slippage_per_side=0.0005):
    values=(entry,exit_price,fee_per_side,slippage_per_side)
    if any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):
        raise ValueError("Nonfinite price or cost")
    if entry<=0 or exit_price<=0 or not (0<=fee_per_side<1) or not (0<=slippage_per_side<1):
        raise ValueError("Invalid price or cost")
    if direction not in ("long","short"):
        raise ValueError("Direction must be long or short")
    side=1 if direction=="long" else -1
    # Execution prices move against the trader on entry and exit.
    actual_entry=entry*(1+side*slippage_per_side)
    actual_exit=exit_price*(1-side*slippage_per_side)
    gross=side*(actual_exit-actual_entry)/actual_entry
    # Both fees charged on executed notionals, expressed per entry notional.
    fees=fee_per_side*(1+actual_exit/actual_entry)
    net=gross-fees
    if not all(math.isfinite(x) for x in (gross,fees,net)):
        raise ValueError("Return arithmetic overflow")
    return {"gross_return":gross,"fee_drag":fees,"net_return":net,
            "actual_entry":actual_entry,"actual_exit":actual_exit}
