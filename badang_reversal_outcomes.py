"""Research-only outcomes for confirmed reversal pivots.

Evaluation uses closed bars strictly after candidate availability; no claim of
profitable trades, and no favorable treatment of unresolved events.
"""
from collections import Counter

def evaluate_reversal_candidates(rows,candidates,*,horizon=24):
    if horizon<1:raise ValueError('horizon must be positive')
    outcomes=[]
    for candidate in candidates:
        start=candidate['available_at_bar']
        if start<0 or start>=len(rows):raise ValueError('invalid availability index')
        end=min(len(rows)-1,start+horizon)
        side=candidate['direction']
        level=float(candidate['confirmation_level'])
        invalidation=float(candidate['invalidation_price'])
        if side not in ('BULLISH','BEARISH'):raise ValueError('invalid direction')
        entry=float(rows[start][4])
        if entry<=0:raise ValueError('invalid reference price')
        status='UNRESOLVED'
        event_bar=None
        # Invalidation and confirmation can both be touched intrabar.
        # Avoid inventing their ordering: classify such bars as AMBIGUOUS.
        for k in range(start+1,end+1):
            hi=float(rows[k][2]);lo=float(rows[k][3])
            invalid=(lo<=invalidation if side=='BULLISH' else hi>=invalidation)
            confirmed=(hi>=level if side=='BULLISH' else lo<=level)
            if invalid and confirmed:
                status='AMBIGUOUS_SAME_BAR';event_bar=k;break
            if invalid:
                status='INVALIDATED';event_bar=k;break
            if confirmed:
                status='STRUCTURE_LEVEL_TOUCHED';event_bar=k;break
        # A structure level touch is not the same as a confirmed closing break.
        signed=1 if side=='BULLISH' else -1
        path=rows[start+1:end+1]
        mfe=max([0.0]+[signed*(float(r[2] if signed>0 else r[3])-entry)/entry for r in path])
        mae=min([0.0]+[signed*(float(r[3] if signed>0 else r[2])-entry)/entry for r in path])
        complete=(end==start+horizon)
        outcomes.append({'direction':side,'available_at_bar':start,'event_bar':event_bar,
            'status':status,'horizon_complete':complete,
            'max_favorable_excursion':mfe,'max_adverse_excursion':mae,
            'entry_reference_close':entry,'trading_pnl':'NOT_EVALUATED'})
    counts=Counter(x['status'] for x in outcomes)
    return {'horizon_bars':horizon,'total':len(outcomes),
        'counts':dict(counts),'events':outcomes,
        'caveat':'Price level touches are not executable trades or confirmed closing breaks'}
