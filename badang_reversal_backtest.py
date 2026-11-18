"""Read-only reversal experiment. Rules are fixed before evaluating holdout.

Not original BADANG scoring. Signals use confirmed pivots and closed-bar
structure breaks; next-open fills, stop-first collisions and fees are explicit.
"""
from badang_reversal_research import reversal_candidates

def reversal_signals(rows,kind):
    if kind not in ('EARLY','CONFIRMED'):raise ValueError('unknown kind')
    out=[]
    for c in reversal_candidates(rows):
        bar=c['available_at_bar'] if kind=='EARLY' else c['confirmed_at_bar']
        if bar is None or bar+1>=len(rows):continue
        # If early candidate already invalidated before next open, skip it.
        if kind=='EARLY' and c.get('invalidated_at_bar') is not None and c['invalidated_at_bar']<=bar:
            continue
        side='LONG' if c['direction']=='BULLISH' else 'SHORT'
        stop=float(c['invalidation_price'])
        if stop<=0:continue
        # Signal construction must not inspect the next bar's open.
        # Entry viability and the 2R target are execution-time decisions.
        out.append({'bar':bar,'side':side,'stop':stop,
                    'kind':kind,'known_at_bar':bar,'signal_timestamp':rows[bar][0]})
    return sorted(out,key=lambda s:s['bar'])

def replay(rows,kind,*,fee=0.0006,slippage=0.0003):
    signals=reversal_signals(rows,kind)
    split=int(len(rows)*0.7)
    trades=[]
    last_exit=-1
    for s in signals:
        bar=s['bar']
        if bar<=last_exit:continue
        side=s['side'];entry=float(rows[bar+1][1])
        stop=s['stop']
        risk=entry-stop if side=='LONG' else stop-entry
        if risk<=0:continue
        target=entry+2*risk if side=='LONG' else entry-2*risk
        if target<=0:continue
        exit_reason='END_OF_DATA';exit_bar=len(rows)-1;exit_price=float(rows[-1][4])
        for k in range(bar+1,len(rows)):
            op=float(rows[k][1]);hi=float(rows[k][2]);lo=float(rows[k][3])
            stop_hit=lo<=stop if side=='LONG' else hi>=stop
            target_hit=hi>=target if side=='LONG' else lo<=target
            if stop_hit:
                exit_reason='STOP';exit_bar=k
                exit_price=min(stop,op) if side=='LONG' else max(stop,op)
                break
            if target_hit:
                exit_reason='TARGET';exit_bar=k;exit_price=target;break
        last_exit=exit_bar
        sign=1 if side=='LONG' else -1
        net=sign*(exit_price-entry)/entry-2*(fee+slippage)
        trades.append({'signal_bar':bar,'entry_bar':bar+1,'exit_bar':exit_bar,
            'side':side,'kind':kind,'entry':entry,'stop':stop,'target':target,
            'exit_reason':exit_reason,'net_return':net,
            'partition':'TRAIN' if bar<split else 'HOLDOUT',
            'crosses_split':bar<split<=exit_bar})
    result={}
    for part in ('TRAIN','HOLDOUT'):
        for side in ('LONG','SHORT'):
            subset=[t for t in trades if t['partition']==part and t['side']==side]
            # Do not score training trades using outcomes from the holdout period.
            completed=[t for t in subset if t['exit_reason']!='END_OF_DATA'
                       and not (part=='TRAIN' and t['crosses_split'])]
            equity=peak=1.0;mdd=0.0;streak=max_streak=0
            for t in completed:
                equity*=max(0,1+t['net_return']);peak=max(peak,equity)
                mdd=max(mdd,(peak-equity)/peak)
                streak=streak+1 if t['net_return']<0 else 0
                max_streak=max(max_streak,streak)
            result[part+'_'+side]={'signals_traded':len(subset),
                'completed_trades':len(completed),
                'censored':sum(t['exit_reason']=='END_OF_DATA' for t in subset),
                'excluded_train_cross_split':sum(part=='TRAIN' and t['crosses_split'] for t in subset),
                'cross_split_trades':sum(t['crosses_split'] for t in subset),
                'win_rate':sum(t['net_return']>0 for t in completed)/len(completed) if completed else None,
                'mean_net_return':sum(t['net_return'] for t in completed)/len(completed) if completed else None,
                'compounded_net_return':equity-1 if completed else None,
                'max_drawdown':mdd if completed else None,
                'max_consecutive_losses':max_streak if completed else None}
    return {'strategy':kind,'research_only':True,'original_badang_score':'NOT_EVALUATED',
        'historical_oi_cvd':'NOT_AVAILABLE','split_bar':split,
        'execution':'NEXT_OPEN_STOP_FIRST','fee_each_side':fee,'slippage_each_side':slippage,
        'signals':len(signals),'trades':trades,'summary':result}
