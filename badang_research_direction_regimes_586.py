"""Causal research attribution by market regime and trade direction.

Regimes are computed at the signal bar; no future prices are used for labels.
This is descriptive research, not a strategy filter or profitability claim.
"""
from badang_research_regimes_555 import regime_at
from badang_research_metrics_546 import summarize_net_returns
from badang_research_ledger_547 import summarize_nonoverlapping_trades

def direction_by_regime(candles, trades, *, lookback=20, threshold=0.03):
    records = list(trades)
    if records:
        summarize_nonoverlapping_trades(records)
    groups = {regime: {side: [] for side in ("long", "short")}
              for regime in ("up", "down", "sideways")}
    for trade in records:
        if not isinstance(trade, dict):
            raise ValueError("Invalid trade record")
        side = trade.get("direction")
        signal = trade.get("signal_index")
        if side not in ("long", "short"):
            raise ValueError("Unknown research trade direction")
        if (type(signal) is not int or signal < 0
                or trade.get("entry_index") != signal + 1
                or trade.get("exit_index", len(candles)) >= len(candles)):
            raise ValueError("Invalid causal research trade timing")
        regime = regime_at(candles, signal, lookback, threshold)
        groups[regime][side].append(trade["net_return"])
    result = {}
    for regime, directions in groups.items():
        result[regime] = {}
        for side, returns in directions.items():
            result[regime][side] = {
                "completed_trades": len(returns),
                "mean_net_return_per_trade": (
                    sum(returns) / len(returns) if returns else None),
                "metrics": summarize_net_returns(returns) if returns else None,
                "conditional_only_not_portfolio": True,
            }
    return {"lookback_bars": lookback, "threshold_fraction": threshold,
            "regime_definition": "signal_time_trailing_close_return",
            "groups": result}
