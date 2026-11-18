"""Read-only, causal reversal candidates from confirmed OHLCV pivots.

Not an Elliott-wave classifier, trading signal, or estimated win probability.
Every candidate becomes visible only after the right-side pivot window closes.
"""
from badang_real_pivot_audit import confirmed_pivots

def reversal_candidates(rows, *, left=3, right=3):
    pivots=confirmed_pivots(rows,left=left,right=right)
    candidates=[]
    for i in range(2,len(pivots)):
        prev,mid,cur=pivots[i-2:i+1]
        if not (prev['type']==cur['type'] and mid['type']!=cur['type']):
            continue
        if cur['type']=='LOW' and cur['price']<prev['price']:
            side='BULLISH'
            confirm_level=mid['price']
            invalidation=cur['price']
            structure='LOWER_LOW'
        elif cur['type']=='HIGH' and cur['price']>prev['price']:
            side='BEARISH'
            confirm_level=mid['price']
            invalidation=cur['price']
            structure='HIGHER_HIGH'
        else:
            continue
        confirmed=cur['confirmed_at_bar']
        # Confirmation uses only later *closed* bars and is timestamped at
        # the first structure break; do not backdate it to the pivot bar.
        confirmation=None
        for k in range(confirmed+1,len(rows)):
            close=float(rows[k][4])
            if (side=='BULLISH' and close>confirm_level) or (side=='BEARISH' and close<confirm_level):
                confirmation=k
                break
            if (side=='BULLISH' and close<invalidation) or (side=='BEARISH' and close>invalidation):
                break
        candidates.append({'direction':side,'status':'EARLY_CANDIDATE',
            'structure':structure,'pivot_bar':cur['pivot_bar'],
            'available_at_bar':confirmed,'available_at_timestamp_ms':rows[confirmed][0],
            'invalidation_price':invalidation,'confirmation_level':confirm_level,
            'confirmed_at_bar':confirmation,
            'confirmation_status':'STRUCTURE_BREAK_OBSERVED' if confirmation is not None else 'NOT_CONFIRMED',
            'elliott_label':'NOT_CLASSIFIED','divergence':'NOT_EVALUATED',
            'historical_oi_cvd':'NOT_AVAILABLE'})
    return candidates
