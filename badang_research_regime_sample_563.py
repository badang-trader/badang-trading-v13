"""Per-regime research sample flags; not statistical proof.

Sparse subsets must never be presented as validated profitability.
"""
from badang_research_sample_554 import assess_sample
from badang_research_regime_metrics_556 import summarize_by_regime

def regime_sample_review(candles,trades,minimum_trades=30,minimum_bars=1000):
    groups=summarize_by_regime(candles,trades)
    result={}
    for label,group in groups.items():
        count=group["trade_count"]
        # The full historical series is not a regime-specific bar count.
        # Do not use its length to claim adequate per-regime exposure.
        assessment=assess_sample(count,0,minimum_trades,minimum_bars)
        result[label]={"trade_count":count,
                       "regime_specific_bars_measured":False,
                       "sample_adequate_for_preliminary_review":False,
                       "profitability_verified":False,
                       "warnings":assessment["warnings"]+["REGIME_EXPOSURE_NOT_MEASURED"]}
    return result
