"""Conservative per-regime sample screening using observed regime exposure.

Screening thresholds are heuristics, not statistical validation.
"""
from badang_research_sample_554 import assess_sample
from badang_research_regime_metrics_556 import summarize_by_regime
from badang_research_regime_exposure_564 import regime_exposure

def regime_sample_review(candles,trades,minimum_trades=30,minimum_bars=1000):
    groups=summarize_by_regime(candles,trades)
    exposure=regime_exposure(candles)
    result={}
    for label,group in groups.items():
        count=group["trade_count"]
        bars=exposure["regime_bars"][label]
        assessment=assess_sample(count,bars,minimum_trades,minimum_bars)
        result[label]={"trade_count":count,
                       "regime_bars":bars,
                       "regime_specific_bars_measured":True,
                       "sample_adequate_for_preliminary_review":assessment["sample_adequate_for_preliminary_review"],
                       "profitability_verified":False,
                       "warnings":assessment["warnings"]}
    return result
