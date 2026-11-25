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
    if not valid:
        return out
    base = next(iter(valid))
    bars = valid[base]
    tr = [max(bars[i][2]-bars[i][3],abs(bars[i][2]-bars[i-1][4]),abs(bars[i][3]-bars[i-1][4])) for i in range(1,len(bars))]
    atr = sum(tr[:14])/14
    for value in tr[14:]:
        atr = (13*atr+value)/14
    out['atr14_wilder'] = atr
    if atr <= 0:
        return out
    out['history'] = [{'time':b[0],'price':b[4]} for b in bars[-24:]]
    out['scan_reference_price'] = price
    out['reference_time'] = bars[-1][0]
    out['reference_time_kind'] = 'CANDLE_OPEN'
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
    all_turns = []
    role_flips = []
    for tf, rows in valid.items():
        turns = confirmed_turns(rows[-160:])
        for t in turns:
            p=t['price']
            later = rows[-160:][t['i']+1:]
            # A broken level is not an intact support/resistance. Role reversal
            # requires separate retest evidence, not merely a historical pivot.
            if t['kind']=='L' and p<price and not any(b[4]<p-tol for b in later):
                points['DOWN'].append((p,tf))
                all_turns.append((p,'L'))
            if t['kind']=='H' and p>price and not any(b[4]>p+tol for b in later):
                points['UP'].append((p,tf))
                all_turns.append((p,'H'))
            # A role flip requires a close beyond the level followed by a distinct retest.
            sign = 1 if t['kind']=='H' else -1
            broken = next((i for i,b in enumerate(later) if (b[4]-p)*sign>tol),None)
            if broken is not None:
                after=later[broken+1:]
                if after and any(b[3]<=p+tol and b[2]>=p-tol and (b[4]-p)*sign>tol for b in after) and all((b[4]-p)*sign>=-tol for b in after):
                    if (price-p)*sign>tol:
                        side='DOWN' if sign>0 else 'UP'
                        points[side].append((p,tf))
                        all_turns.append((p,'L' if sign>0 else 'H'))
                        role_flips.append((p,tf,side))
        for period in (20,50,200):
            if len(rows)<period: continue
            v=sum(b[4] for b in rows[:period])/period
            for b in rows[period:]: v+=(b[4]-v)*2/(period+1)
            ema_levels.append((v,tf))
        structure=(item.get('structure_427') or {}).get(tf,{})
        if structure.get('status')!='OK' or structure.get('last_closed_time')!=rows[-1][0]:
            continue
        for w in (structure.get('wave') or {}).get('alternatives',[]):
            if w.get('stage')!='BREAKOUT_PROGRESS' or w.get('direction') not in ('UP','DOWN'):
                continue
            if w.get('reference_price')!=rows[-1][4]:
                continue
            sign=1 if w['direction']=='UP' else -1
            for target in w.get('future_targets',[]):
                p=_f(target.get('price'))
                if target.get('timeframe')!=tf or target.get('reached') is not False or p is None or p<=0 or (p-price)*sign<=0:
                    continue
                # Shared engine targets are hypotheses, not confirmed endings.
                wave_targets.append((p,w['direction'],tf))
    for side in (('DOWN','UP') if direction=='MIXED' else (direction,)):
        groups=[]
        for p,tf in sorted(points[side],reverse=side=='DOWN'):
            if groups and abs(p-groups[-1][-1][0])<=tol and abs(p-groups[-1][0][0])<=2*tol:
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
            if any(s==side and lo<=p<=hi for p,_,s in role_flips):
                reasons.append('돌파 이후 재시험 확인된 역할 전환')
            # Wave and Fibonacci projections share the same anchors; do not double count.
            if any(s==side and lo<=p<=hi for p,s,_ in wave_targets):
                components['wave']=10; reasons.append('돌파 이후 파동 목표 가설 중첩 (종료 미확정)')
            elif any(s==side and lo<=p<=hi for p,s,_ in fibs):
                components['fibonacci']=15; reasons.append('5파 피보나치 확장 가설 중첩')
            if any(lo<=p<=hi for p,_ in ema_levels):
                components['ema']=10; reasons.append('현재 확정봉 EMA 중첩')
            score=sum(components.values())
            zones.append({'low':lo,'high':hi,'center':center,'expected_score':score,
                          'confirmation_score':None,'expected_score_ceiling':40,'components':components,'reasons':reasons,
                          'unverified':['구간 도달 후 반전 캔들','다이버전스','거래량·OI·CVD'],
                          'probability':None,'change_pct':(center/price-1)*100,
                          'invalidation':lo if side=='DOWN' else hi,
                          'reversal_target':None,'next_target':None})
        for i,z in enumerate(zones):
            if i+1<len(zones): z['next_target']=zones[i+1]['center']
            opposite=[p for p,kind in all_turns if (kind=='H' and p>z['high']+tol if side=='DOWN' else kind=='L' and p<z['low']-tol)]
            targets=sorted(set(opposite),reverse=side=='UP')
            z['near_reversal_target']=targets[0] if targets else None
            z['major_reversal_target']=next((p for p in targets[1:] if abs(p-targets[0])>=atr),None) if targets else None
            z['reversal_target']=z['near_reversal_target']
            z['reversal_change_pct']=(z['reversal_target']/z['center']-1)*100 if z['reversal_target'] is not None else None
        out['paths'].append({'direction':side,'zones':zones})
    return out
