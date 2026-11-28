"""Causal last-closed-candle mark lookup for research, never interpolation.

A stale close is an observed historical price, not a current exchange mark.
"""
from bisect import bisect_right

FRAME_MS={'15m':900000,'30m':1800000,'1H':3600000,'4H':14400000,'1D':86400000}

def observed_mark(rows,timeframe,asof_ts_ms,*,max_age_ms=None):
    step=FRAME_MS[timeframe]
    if max_age_ms is not None and max_age_ms<0:raise ValueError('negative maximum age')
    closes=[int(r[0])+step for r in rows]
    if closes!=sorted(closes) or len(closes)!=len(set(closes)):
        raise ValueError('unordered or duplicated candle closes')
    index=bisect_right(closes,int(asof_ts_ms))-1
    if index<0:
        return {'status':'NO_PAST_CLOSED_PRICE','price':None,'age_ms':None}
    age=int(asof_ts_ms)-closes[index]
    stale=max_age_ms is not None and age>max_age_ms
    return {'status':'STALE_OBSERVED_CLOSE' if stale else
            ('EXACT_CLOSE' if age==0 else 'LAST_KNOWN_CLOSED_PRICE'),
            'price':float(rows[index][4]),'close_ts_ms':closes[index],
            'age_ms':age,'not_exchange_mark_price':True,
            'not_interpolated':True,'eligible_for_strict_equity':age==0}
