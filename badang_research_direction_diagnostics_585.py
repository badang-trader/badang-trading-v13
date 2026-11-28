"""Read-only attribution of fixed-horizon research losses by trade direction."""
from badang_research_ledger_547 import summarize_nonoverlapping_trades

def direction_diagnostics(trades):
    records = list(trades)
    result = {}
    for direction in ("long", "short"):
        subset = [t for t in records if t.get("direction") == direction]
        metrics = summarize_nonoverlapping_trades(subset) if subset else None
        result[direction] = {
            "completed_trades": len(subset),
            "metrics": metrics,
            "mean_net_return_per_trade": (
                sum(t["net_return"] for t in subset) / len(subset)
                if subset else None),
        }
    if sum(v["completed_trades"] for v in result.values()) != len(records):
        raise ValueError("Unexpected trade direction in research ledger")
    return result
