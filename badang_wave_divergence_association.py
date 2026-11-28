"""Causal association of confirmed RSI/MACD divergences with wave hypotheses.

Strictly earlier bars only: same-bar confirmation order is unknowable from OHLC.
"""
from collections import Counter

def associate_prior_divergences(scenarios,divergences,*,lookback=24):
    if not isinstance(lookback,int) or lookback<1:raise ValueError('invalid lookback')
    output=[]
    for scenario in scenarios:
        at=scenario['available_at_bar']
        earlier=[d for d in divergences if at-lookback<=d['available_at_bar']<at]
        same=[d for d in divergences if d['available_at_bar']==at]
        counts=Counter(d['classification']+'_'+d['indicator'] for d in earlier)
        output.append({'scenario':scenario['scenario'],'available_at_bar':at,
            'strictly_prior_divergences':len(earlier),
            'prior_by_type_indicator':dict(counts),
            'same_bar_unordered':len(same),
            'later_divergences_excluded':sum(d['available_at_bar']>at for d in divergences),
            'wave_status':scenario['status'],
            'caveat':'Association is temporal, not a causal or profitable prediction'})
    return output
