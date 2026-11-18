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
            'invalidation_price':None,
            'terminal_reference_price':prices[5],
            'invalidation_status':'NOT_VALIDATED_FOR_WAVE_DEGREE',
            'confirmation_lag_bars':p[-1]['confirmed_at_bar']-p[-1]['pivot_bar'],
            'retracement_382':prices[5]-sign*span*.382,
            'retracement_618':prices[5]-sign*span*.618,
            'caveat':'Illustrative 5-leg geometry only; wave degree, extension, ABC and trade outcome unverified'})
    return scenarios

def abc_scenarios(rows):
    """Find three alternating legs consistent with a possible zigzag-like ABC.

    Geometry is descriptive, not a validated 5-3-5 subdivision or prediction.
    """
    pivots=_alternating(confirmed_pivots(rows))
    result=[]
    for k in range(3,len(pivots)):
        p=pivots[k-3:k+1]
        prices=[float(x['price']) for x in p]
        direction=1 if p[0]['type']=='HIGH' else -1
        a=direction*(prices[0]-prices[1])
        b=direction*(prices[2]-prices[1])
        c=direction*(prices[2]-prices[3])
        if not (a>0 and 0<b<a and c>0):continue
        if c<0.618*a or c>1.618*a:continue
        # C beyond A end is a possible zigzag, not a universal ABC rule.
        if direction*(prices[1]-prices[3])<=0:continue
        result.append({'status':'UNVALIDATED_ABC_GEOMETRY',
            'scenario':'POSSIBLE_ABC_ZIGZAG_END',
            'correction_direction':'DOWN' if direction==1 else 'UP',
            'pivot_bars':[x['pivot_bar'] for x in p],
            'available_at_bar':p[-1]['confirmed_at_bar'],
            'available_at_timestamp_ms':rows[p[-1]['confirmed_at_bar']][0],
            'terminal_price':prices[3],
            'a_length':a,'b_retracement_ratio':b/a,'c_to_a_ratio':c/a,
            'alternative':'COMPLEX_CORRECTION_OR_TREND_CONTINUATION',
            'invalidation_price':None,
            'terminal_reference_price':prices[3],
            'invalidation_status':'NOT_VALIDATED_FOR_WAVE_DEGREE',
            'confirmation_lag_bars':p[-1]['confirmed_at_bar']-p[-1]['pivot_bar'],
            'retracement_382':prices[3]+direction*abs(prices[0]-prices[3])*.382,
            'retracement_618':prices[3]+direction*abs(prices[0]-prices[3])*.618,
            'caveat':'Zigzag-like geometry only; internal 5-3-5 and wave degree unverified'})
    return result
