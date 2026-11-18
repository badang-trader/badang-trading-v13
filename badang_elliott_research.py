"""Exploratory Elliott-like pivot geometry, never a certified wave count.

All scenarios use confirmed alternating pivots. A candidate is only known
at the final pivot confirmation; no future bars are needed to label it.
"""
from badang_real_pivot_audit import confirmed_pivots

def _alternating(pivots):
    out=[]
    for p in pivots:
        if out and p['type']==out[-1]['type']:
            prev=out[-1]
            if (p['type']=='HIGH' and p['price']>prev['price']) or (p['type']=='LOW' and p['price']<prev['price']):
                out[-1]=p
        else:out.append(p)
    return out

def wave_scenarios(rows):
    pivots=_alternating(confirmed_pivots(rows))
    scenarios=[]
    for k in range(5,len(pivots)):
        p=pivots[k-5:k+1]
        if any(x['confirmed_at_bar']>p[-1]['confirmed_at_bar'] for x in p):continue
        prices=[float(x['price']) for x in p]
        bullish=p[0]['type']=='LOW'
        sign=1 if bullish else -1
        legs=[sign*(prices[j+1]-prices[j]) for j in range(5)]
        # Impulse geometry: 1/3/5 in trend direction, 2/4 countertrend.
        if not (legs[0]>0 and legs[1]<0 and legs[2]>0 and legs[3]<0 and legs[4]>0):continue
        if not (sign*(prices[2]-prices[0])>0 and sign*(prices[4]-prices[1])>0):continue
        if legs[2]<min(legs[0],legs[4]):continue # third cannot be shortest
        if sign*(prices[4]-prices[1])<=0:continue # wave 4 overlap excluded
        span=abs(prices[5]-prices[0])
        if span<=0:continue
        scenarios.append({'status':'UNVALIDATED_IMPULSE_GEOMETRY',
            'scenario':'POSSIBLE_FIVE_WAVE_END','direction':'UP' if bullish else 'DOWN',
            'pivot_bars':[x['pivot_bar'] for x in p],
            'available_at_bar':p[-1]['confirmed_at_bar'],
            'available_at_timestamp_ms':rows[p[-1]['confirmed_at_bar']][0],
            'terminal_price':prices[5],
            'alternative':'TREND_EXTENSION_OR_DIFFERENT_WAVE_DEGREE',
            'invalidation_price':prices[5],
            'retracement_382':prices[5]-sign*span*.382,
            'retracement_618':prices[5]-sign*span*.618,
            'caveat':'Illustrative 5-leg geometry only; wave degree, extension, ABC and trade outcome unverified'})
    return scenarios
