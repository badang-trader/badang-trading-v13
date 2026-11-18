"""Read-only adapter: use the EXISTING BADANG analysis/scoring logic on historical prefixes.

No network, orders, flow fabrication, or hindsight scores. Higher/lower frames
must be supplied as closed prefixes aligned to the setup bar's close time.
If genuine historical order-flow is unavailable, do not infer BUY/SELL.
"""
from app import ema,rsi,divergence,score_direction,scenario

def analyze_closed_prefix(rows):
    if len(rows)<205: return None
    c=[float(r[4]) for r in rows];h=[float(r[2]) for r in rows]
    l=[float(r[3]) for r in rows];v=[float(r[5]) for r in rows]
    e20=ema(c,20);e50=ema(c,50);e200=ema(c,200)
    rs=rsi(c);mac=ema(c,12)[-1]-ema(c,26)[-1]
    mac_series=[a-b for a,b in zip(ema(c,12),ema(c,26))]
    sig=ema(mac_series,9)[-1]
    avg=sum(v[-21:-1])/20
    ratio=v[-1]/avg if avg else 0
    price=c[-1]
    up=e20[-1]>e50[-1]>e200[-1]
    down=e20[-1]<e50[-1]<e200[-1]
    div=divergence(c,[50.]*15+[rsi(c[:k]) for k in range(16,len(c)+1)])
    br_up=price>max(h[-21:-1]) and ratio>=1.2
    br_down=price<min(l[-21:-1]) and ratio>=1.2
    position=(price-l[-1])/max(h[-1]-l[-1],1e-12)
    tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]
    atr=sum(tr[-14:])/14
    return {'price':price,'trend':'UP' if up else 'DOWN' if down else 'MIXED',
            'rsi':round(rs,1),'volume_ratio':round(ratio,2),'divergence':div,
            'fake_breakout':(br_up and position<.65) or (br_down and position>.35),
            'atr':atr,'swing_low':min(l[-11:-1]),'swing_high':max(h[-11:-1]),
            'macd':mac,'macd_signal':sig}

def score_historical_prefixes(setup_rows,lower_rows,higher_rows,mode,flow=None,
                              *, setup_frame=None, lower_frame=None, higher_frame=None):
    # Fail closed unless each timeframe's last bar had actually CLOSED by
    # the setup bar close. A higher-frame bar that ends later is lookahead.
    from badang_historical_integrity import FRAME_MS
    frames=(setup_frame,lower_frame,higher_frame)
    if any(frame not in FRAME_MS for frame in frames):
        return {'status':'TIMEFRAME_PROVENANCE_MISSING','signal':None}
    inputs=(setup_rows,lower_rows,higher_rows)
    if any(not rows for rows in inputs):
        return {'status':'HISTORICAL_BARS_MISSING','signal':None}
    try:
        setup_end=int(setup_rows[-1][0])+FRAME_MS[setup_frame]
        for rows,frame in zip(inputs,frames):
            if int(rows[-1][0])+FRAME_MS[frame]>setup_end:
                return {'status':'FUTURE_TIMEFRAME_BAR_REJECTED','signal':None}
    except (ValueError,TypeError,IndexError):
        return {'status':'INVALID_TIMEFRAME_TIMESTAMP','signal':None}
    if mode not in ('scalp','swing'):raise ValueError('invalid mode')
    setup=analyze_closed_prefix(setup_rows)
    lower=analyze_closed_prefix(lower_rows)
    higher=analyze_closed_prefix(higher_rows)
    if not all((setup,lower,higher)):return None
    if flow is None or flow.get('source')!='HISTORICAL_OBSERVED':
        return {'status':'HISTORICAL_FLOW_MISSING','signal':None,
                'reason':'실제 당시 수급 기록이 없어 기존 BADANG 15점 항목 검증 불가'}
    if flow.get('state') not in ('BUY','SELL','NEUTRAL'):
        return {'status':'INVALID_FLOW','signal':None}
    scores={side:score_direction(setup,higher['trend'],flow,side,lower)
            for side in ('LONG','SHORT')}
    side=max(scores,key=scores.get)
    expected='UP' if side=='LONG' else 'DOWN'
    opposite='bearish' if side=='LONG' else 'bullish'
    aligned=setup['trend']==expected and higher['trend']==expected
    flow_ok=flow['state']==('BUY' if side=='LONG' else 'SELL')
    safe=(not setup['fake_breakout'] and setup['divergence']!=opposite
          and lower['divergence']!=opposite)
    if not (scores[side]>=65 and aligned and flow_ok and safe):
        return {'status':'WAIT_HISTORICAL_CONDITIONS_NOT_MET',
                'signal':None,'scores':scores,
                'conditions':{'aligned':aligned,'flow_ok':flow_ok,'safe':safe}}
    plan=scenario(setup,side,mode)
    if not plan:return {'status':'NO_VALID_PLAN','signal':None,'scores':scores}
    return {'status':'EVALUATED_HISTORICAL_PREFIX','signal':{'side':side,
            'score':scores[side],'stop':plan['stop'],'target':plan['tp1']},
            'scores':scores,'plan':plan,
            'note':'historical flow must be independently authenticated'}
