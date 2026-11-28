"""Causal Elliott scenario replay on successive closed-candle prefixes.

A pivot requiring right-hand confirmation cannot be acted on before those
candles close. This is a diagnostic, not a predictive backtest or order engine.
"""
from badang_wave_choice_response_587 import wave_choice_response

def replay_wave_scenarios(candles, *, warmup=205, stride=1):
    if type(warmup) is not int or warmup < 25:
        raise ValueError("warmup must be at least 25 closed candles")
    if type(stride) is not int or stride < 1:
        raise ValueError("stride must be a positive integer")
    if not isinstance(candles, (list, tuple)):
        raise ValueError("Expected a sequence of confirmed candles")
    records = []
    for end in range(warmup, len(candles) + 1, stride):
        snapshot = wave_choice_response(candles[:end])
        if snapshot["status"] == "invalid_data":
            raise ValueError("Invalid historical candle in causal replay")
        records.append({
            "asof_closed_bar_index": end - 1,
            "status": snapshot["status"],
            "candidate_count": len(snapshot["scenarios"]),
            "scenarios": snapshot["scenarios"],
            "trading_ready": False,
        })
    return {"status": "research_only", "causal_prefix_only": True,
            "automatic_orders": False, "trading_ready": False,
            "observations": records}
