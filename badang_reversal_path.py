"""Conditional reversal zones, not probabilities or order signals."""
from badang_decision_427 import closed_bars, confirmed_turns, _f

def reversal_path(item, frame_data, mode, now_ms):
    price = _f(item.get('analysis_reference_price'))
    frames = ('5m','15m','30m','1H') if mode == 'scalp' else ('1H','4H','1D')
    valid = {}
    for tf in frames:
        rec = frame_data.get(tf) or {}
        if str(rec.get('exchange','')).lower() != 'bitget':
            continue
        bars, _ = closed_bars(rec.get('candles'), tf, now_ms)
        if bars:
            valid[tf] = bars
    out = {'status':'UNAVAILABLE','reference_price':price,'probability_status':'NOT_BACKTEST_VALIDATED',
           'probability':None,'valid_frames':list(valid),'required_frames':list(frames),'paths':[],
           'history':[], 'score_is_probability':False}
    if not price or price <= 0 or not valid:
        return out
    base = next(iter(valid))
    bars = valid[base]
    atr = sum(max(bars[i][2]-bars[i][3],abs(bars[i][2]-bars[i-1][4]),abs(bars[i][3]-bars[i-1][4])) for i in range(len(bars)-14,len(bars)))/14
    if atr <= 0:
        return out
    out['history'] = [{'time':b[0],'price':b[4]} for b in bars[-24:]]
    out['reference_time'] = bars[-1][0]
    out['history_timeframe'] = base
    out['reference_price'] = price = bars[-1][4]
    trends = item.get('timeframe_trends') or {}
    directions = {trends.get(tf) for tf in valid}
    direction = 'DOWN' if directions == {'DOWN'} else 'UP' if directions == {'UP'} else 'MIXED'
    out['trend'] = direction
    out['status'] = 'AVAILABLE'
    tol = atr * .25
    points = {'DOWN':[], 'UP':[]}
    ema_levels = []
    fibs = []
    wave_targets = []
    for tf, rows in valid.items():
        turns = confirmed_turns(rows[-160:])
        for t in turns:
            p=t['price']
            if t['kind']=='L' and p<price: points['DOWN'].append((p,tf))
            if t['kind']=='H' and p>price: points['UP'].append((p,tf))
        for period in (20,50,200):
            if len(rows)<period: continue
            v=sum(b[4] for b in rows[:period])/period
            for b in rows[period:]: v+=(b[4]-v)*2/(period+1)
            ema_levels.append((v,tf))
        structure=(item.get('structure_427') or {}).get(tf,{})
        for w in (structure.get('wave') or {}).get('alternatives',[]):
            p=w.get('pivot_prices',[])
            if w.get('wave')==5 and len(p)==5 and w.get('direction') in ('UP','DOWN'):
                sign=1 if w['direction']=='UP' else -1
                target=p[4]+sign*abs(p[1]-p[0])
                if target>0: wave_targets.append((target,w['direction'],tf))
                for ratio in (.618,1.618):
                    target=p[4]+sign*abs(p[1]-p[0])*ratio
                    if target>0: fibs.append((target,w['direction'],tf))
    for side in (('DOWN','UP') if direction=='MIXED' else (direction,)):
        groups=[]
        for p,tf in sorted(points[side],reverse=side=='DOWN'):
            if groups and abs(p-groups[-1][0][0])<=tol:
                groups[-1].append((p,tf))
            else: groups.append([(p,tf)])
        zones=[]
        for group in groups[:3]:
            vals=[p for p,_ in group]; center=sum(vals)/len(vals)
            lo=max(price*1e-9,min(vals)-tol/2); hi=max(vals)+tol/2
            if side=='DOWN': hi=min(hi,price)
            else: lo=max(lo,price)
            tfs=sorted(set(tf for _,tf in group))
            components={'structure':min(20,8+6*(len(tfs)-1)), 'wave':0,'fibonacci':0,'ema':0}
            reasons=['확정 스윙 지지·저항: '+', '.join(tfs)]
            # Wave and Fibonacci projections share the same anchors; do not double count.
            if any(s==side and lo<=p<=hi for p,s,_ in wave_targets):
                components['wave']=20; reasons.append('일반 5파 길이 가설 중첩')
            elif any(s==side and lo<=p<=hi for p,s,_ in fibs):
                components['fibonacci']=15; reasons.append('5파 피보나치 확장 가설 중첩')
            if any(lo<=p<=hi for p,_ in ema_levels):
                components['ema']=10; reasons.append('현재 확정봉 EMA 중첩')
            score=sum(components.values())
            zones.append({'low':lo,'high':hi,'center':center,'expected_score':score,
                          'confirmation_score':None,'components':components,'reasons':reasons,
                          'unverified':['구간 도달 후 반전 캔들','다이버전스','거래량·OI·CVD'],
                          'probability':None,'change_pct':(center/price-1)*100,
                          'invalidation':lo if side=='DOWN' else hi,
                          'reversal_target':None,'next_target':None})
        for i,z in enumerate(zones):
            if i+1<len(zones): z['next_target']=zones[i+1]['center']
            opposite=[p for p,_ in points['UP' if side=='DOWN' else 'DOWN'] if (p>z['high'] if side=='DOWN' else p<z['low'])]
            if opposite: z['reversal_target']=min(opposite) if side=='DOWN' else max(opposite)
        out['paths'].append({'direction':side,'zones':zones})
    return out
