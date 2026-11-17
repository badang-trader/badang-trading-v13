"""Read-only, walk-forward trade outcome audit. No exchange or order access.

Caller supplies historical *closed* OHLC candles and historical signals that
were available at signal_bar close. Execute at next bar open, not signal close.
No performance numbers are reported until actual history is supplied.
"""
import math

def _finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def score_band(score):
    if not _finite(score) or score < 80: return None
    if score < 85: return '80-84'
    if score < 90: return '85-89'
    return '90+'

def audit_trades(candles, signals, *, fee_rate=0.0006, slippage_rate=0.0003):
    """OHLC: (timestamp, open, high, low, close); signals: bar, side, score, stop, target, mode.

    Conservative convention: if stop and target touch same bar, stop wins.
    At most one active position; each trade closes at stop/target or final close.
    Returns simple fractional price returns net of entry/exit fees/slippage,
    not leveraged PnL. Requires precomputed historical signals; NEVER uses
    current scan output to fabricate a historical win rate.
    """
    if any(not _finite(x) or x < 0 or x >= 1 for x in (fee_rate,slippage_rate)):
        raise ValueError('invalid fee/slippage')
    if len(candles)<3: raise ValueError('insufficient closed candles')
    prior=None
    for row in candles:
        if len(row)<5: raise ValueError('invalid candle')
        ts,op,hi,lo,cl=row[:5]
        if not all(_finite(x) for x in (ts,op,hi,lo,cl)) or min(op,lo,cl)<=0 or hi<max(op,cl) or lo>min(op,cl):
            raise ValueError('invalid candle')
        if prior is not None and ts<=prior: raise ValueError('duplicate or unsorted timestamps')
        prior=ts
    trades=[]
    last_exit=-1
    for s in sorted(signals,key=lambda x:x['bar']):
        bar=s['bar'];side=s['side'];stop=s['stop'];target=s['target']
        # A historical signal must be timestamped at the bar where it was
        # actually available. Reject future/repainted signals when metadata exists.
        if 'known_at_bar' not in s or s['known_at_bar'] != bar:
            continue
        if not isinstance(bar,int) or isinstance(bar,bool) or bar<0 or bar+1>=len(candles) or bar<=last_exit: continue
        band=score_band(s['score'])
        if band is None or side not in ('LONG','SHORT'): continue
        entry=candles[bar+1][1]
        if not all(_finite(x) and x>0 for x in (stop,target)): continue
        if side=='LONG' and not (stop<entry<target): continue
        if side=='SHORT' and not (target<entry<stop): continue
        exit_bar=len(candles)-1
        exit_price=candles[-1][4]
        for k in range(bar+1,len(candles)):
            hi,lo=candles[k][2],candles[k][3]
            hit_stop=lo<=stop if side=='LONG' else hi>=stop
            hit_target=hi>=target if side=='LONG' else lo<=target
            if hit_stop or hit_target:
                exit_bar=k
                # Opening gaps beyond stop/target must not receive a better stop fill.
                op=candles[k][1]
                if hit_stop:
                    exit_price=min(stop,op) if side=='LONG' else max(stop,op)
                else:
                    exit_price=target
                break
        sign=1 if side=='LONG' else -1
        gross=sign*(exit_price-entry)/entry
        net=gross-2*(fee_rate+slippage_rate)
        trades.append({'mode':s.get('mode','UNSPECIFIED'),'side':side,'band':band,
                       'signal_bar':bar,'entry_bar':bar+1,'exit_bar':exit_bar,
                       'gross_return':gross,'net_return':net})
        last_exit=exit_bar
    groups={}
    for t in trades:
        key=(t['mode'],t['side'],t['band'])
        groups.setdefault(key,[]).append(t)
    summary=[]
    for (mode,side,band),items in sorted(groups.items()):
        equity=1.;peak=1.;mdd=0.;losing=0;max_losing=0
        for t in items:
            equity*=max(0.,1+t['net_return'])
            peak=max(peak,equity)
            mdd=max(mdd,(peak-equity)/peak)
            losing=losing+1 if t['net_return']<0 else 0
            max_losing=max(max_losing,losing)
        summary.append({'mode':mode,'side':side,'score_band':band,'samples':len(items),
                        'win_rate':sum(t['net_return']>0 for t in items)/len(items),
                        'mean_net_return':sum(t['net_return'] for t in items)/len(items),
                        'compounded_net_return':equity-1,'max_drawdown':mdd,
                        'max_consecutive_losses':max_losing})
    return {'status':'HISTORICAL_SIGNALS_REQUIRED' if not signals else
                     'EVALUATED' if trades else 'NO_ELIGIBLE_HISTORICAL_SIGNALS',
            'assumptions':{'fee_rate_per_side':fee_rate,'slippage_rate_per_side':slippage_rate,
                           'entry':'next_bar_open','same_bar_collision':'stop_first',
                           'position_limit':1,'leverage':1},
            'trades':trades,'groups':summary}
