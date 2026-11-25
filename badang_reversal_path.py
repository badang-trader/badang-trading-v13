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
        # Retracement of the latest confirmed swing; no wave projection reused.
        if len(turns)>=2:
            start,end=turns[-2:]
            delta=end['price']-start['price']
            side='DOWN' if delta>0 else 'UP'
            if delta and all((b[4]-start['price'])*(1 if delta>0 else -1)>0 for b in rows[-160:][end['i']+1:]):
                for ratio in (.382,.5,.618,.786):
                    level=end['price']-delta*ratio
                    if level>0 and (level<price if side=='DOWN' else level>price):
                        fibs.append((level,side,tf))
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
    divergences=[dict(d,timeframe=tf) for tf,rows in valid.items() for d in reversal_divergences(rows)]
    # Historical reactions are evidence available before the forecast.
    reactions = []
    for tf, rows in valid.items():
        for t in confirmed_turns(rows[-160:]):
            idx=len(rows)-min(160,len(rows))+t['i']
            if idx<20 or idx+3>=len(rows):
                continue
            p=t['price']
            sign=1 if t['kind']=='L' else -1
            prior=sum(b[5] for b in rows[idx-20:idx])/20
            later=rows[idx+1:idx+4]
            if prior>0 and rows[idx][5]>=1.5*prior and (later[-1][4]-p)*sign>=atr:
                if not any((b[4]-p)*sign < -tol for b in rows[idx+1:]):
                    reactions.append((p,'DOWN' if sign>0 else 'UP',tf))
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
            components={'structure':min(20,8+6*(len(tfs)-1)), 'wave':0,'fibonacci':0,'ema':0,'volume':0,'divergence':0}
            reasons=['확정 스윙 지지·저항: '+', '.join(tfs)]
            if any(s==side and lo<=p<=hi for p,_,s in role_flips):
                reasons.append('돌파 이후 재시험 확인된 역할 전환')
            # Wave and Fibonacci projections share the same anchors; do not double count.
            if any(s==side and lo<=p<=hi for p,s,_ in wave_targets):
                components['wave']=10; reasons.append('돌파 이후 파동 목표 가설 중첩 (종료 미확정)')
            elif any(s==side and lo<=p<=hi for p,s,_ in fibs):
                components['fibonacci']=10; reasons.append('최근 확정 스윙 피보나치 되돌림 중첩')
            if any(lo<=p<=hi for p,_ in ema_levels):
                components['ema']=10; reasons.append('현재 확정봉 EMA 중첩')
            volume_available=any(len(rows)>=24 and any(b[5]>0 for b in rows[-160:]) for rows in valid.values())
            if any(s==side and lo<=p<=hi for p,s,_ in reactions):
                components['volume']=5
                reasons.append('과거 확정 피벗 거래량 증가 및 가격 반응')
            matches=[d for d in divergences if d['type']=='REGULAR' and d['side']==side and lo<=d['price']<=hi]
            if matches:
                components['divergence']=10
                reasons.append('유효한 일반 다이버전스: '+', '.join(sorted(set(d['indicator'] for d in matches))))
            ceiling=50+(5 if volume_available else 0)
            score=sum(components.values())
            zones.append({'low':lo,'high':hi,'center':center,'expected_score':score,
                          'confirmation_score':None,'expected_score_ceiling':ceiling,'components':components,'reasons':reasons,
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
    out['divergences']=divergences
    return out


def confirmation_review(zone, side, rows, touched_index):
    """Evaluate only candles observed after a recorded zone touch."""
    if touched_index is None:
        return {'confirmation_score':None,'state':'BEFORE_TOUCH'}
    if not 0<=touched_index<len(rows) or side not in ('DOWN','UP'):
        raise ValueError('invalid touch or direction')
    sign=1 if side=='DOWN' else -1
    lo,hi=zone['low'],zone['high']
    observed=rows[touched_index:]
    for b in observed:
        if (b[3]<=zone['invalidation'] if sign>0 else b[2]>=zone['invalidation']):
            return {'confirmation_score':None,'state':'INVALIDATED','invalidated_at':b[0]}
    b=observed[-1]
    span=b[2]-b[3]
    body=(b[4]-b[1])*sign
    wick=min(b[1],b[4])-b[3] if sign>0 else b[2]-max(b[1],b[4])
    outside=(b[4]>hi if sign>0 else b[4]<lo)
    components={'candle':0,'volume':0,'retest':0,'structure':0,'momentum':0}
    maxima={'candle':15,'volume':0,'retest':0,'structure':0,'momentum':0}
    if span>0 and body>0 and wick>=span*.35 and outside:
        components['candle']=15
    if len(rows)>=21:
        avg=sum(x[5] for x in rows[-21:-1])/20
        if avg>0:
            maxima['volume']=10
            if b[5]>=1.5*avg and body>0 and outside:
                components['volume']=10
    if len(observed)>=3:
        maxima['retest']=15
        if any((x[4]>hi if sign>0 else x[4]<lo) for x in observed[:-1]) and b[3]<=hi and b[2]>=lo and outside:
            components['retest']=15
        maxima['structure']=20
        if outside and (b[4]>max(x[2] for x in observed[-3:-1]) if sign>0 else b[4]<min(x[3] for x in observed[-3:-1])):
            components['structure']=20
    if len(observed)>=4:
        maxima['momentum']=10
        if (b[4]-observed[-2][4])*sign>max(0,(observed[-2][4]-observed[-4][4])*sign/2) and outside:
            components['momentum']=10
    maxima['divergence']=0
    components['divergence']=0
    if len(rows)>=40:
        maxima['divergence']=20
        matches=[d for d in reversal_divergences(rows)
                 if d['type']=='REGULAR' and d['side']==side
                 and d['pivot_time']>=observed[0][0]
                 and lo<=d['price']<=hi]
        if matches:
            components['divergence']=15
            if len(set(d['indicator'] for d in matches))>1:
                components['divergence']=20
    # A touch candle cannot establish the order of touch and target.
    targets={}
    for key in ('near_reversal_target','major_reversal_target'):
        p=zone.get(key)
        targets[key]=next((x[0] for x in observed[1:] if p is not None and (x[2]>=p if sign>0 else x[3]<=p)),None)
    return {'confirmation_score':sum(components.values()),'confirmation_score_ceiling':sum(maxima.values()),
            'confirmation_components':components,'confirmation_maxima':maxima,
            'state':'TOUCHED','touch_time':observed[0][0],'evaluated_at':b[0],
            'target_times':targets,'unverified':['OI/CVD'],
            'score_is_probability':False}



def track_reversals(conn, symbol, mode, path, frame_data, now_ms):
    """Immutable forecasts and append-only candle evaluations in PostgreSQL."""
    import json
    import hashlib
    from psycopg2.extras import Json
    tf=path.get('history_timeframe')
    if not tf or path.get('status')!='AVAILABLE':
        return {'status':'NO_VALID_FRAME'}
    rows,_=closed_bars((frame_data.get(tf) or {}).get('candles'),tf,now_ms)
    if not rows:
        return {'status':'NO_VALID_FRAME'}
    step={'5m':300000,'15m':900000,'30m':1800000,'1H':3600000,'4H':14400000,'1D':86400000}[tf]
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",('reversal514:'+symbol+':'+mode+':'+tf,))
            cur.execute("""CREATE TABLE IF NOT EXISTS badang_reversal_forecast_514 (
                id TEXT PRIMARY KEY, symbol TEXT NOT NULL, mode TEXT NOT NULL, tf TEXT NOT NULL,
                reference_ms BIGINT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                direction TEXT NOT NULL, forecast JSONB NOT NULL)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS badang_reversal_event_514 (
                forecast_id TEXT REFERENCES badang_reversal_forecast_514(id),
                candle_ms BIGINT NOT NULL, result JSONB NOT NULL,
                PRIMARY KEY(forecast_id,candle_ms))""")
            cur.execute("""SELECT f.id,f.reference_ms,f.direction,f.forecast,e.candle_ms,e.result
                FROM badang_reversal_forecast_514 f LEFT JOIN LATERAL
                (SELECT candle_ms,result FROM badang_reversal_event_514 WHERE forecast_id=f.id ORDER BY candle_ms DESC LIMIT 1) e ON true
                WHERE f.symbol=%s AND f.mode=%s AND f.tf=%s
                AND COALESCE(e.result->>'state','') NOT IN ('INVALIDATED','EXPIRED','DATA_GAP','MAJOR_TARGET')""",(symbol,mode,tf))
            active=cur.fetchall()
            tracked=[]
            for fid,ref,side,z,last,prev in active:
                prev=prev or {}
                touch=prev.get('touch_time')
                cursor=last if last is not None else ref
                pending=[(i,b) for i,b in enumerate(rows) if b[0]>cursor]
                for i,b in pending:
                    if b[0]!=cursor+step:
                        result={'state':'DATA_GAP','touch_time':touch}
                    elif b[0]-ref>48*step:
                        result={'state':'EXPIRED','touch_time':touch}
                    else:
                        if touch is None and b[3]<=z['high'] and b[2]>=z['low']:
                            touch=b[0]
                        ti=next((j for j,x in enumerate(rows[:i+1]) if x[0]==touch),None)
                        if touch is not None and ti is None:
                            result={'state':'DATA_GAP','touch_time':touch}
                        elif (b[3]<=z['invalidation'] if side=='DOWN' else b[2]>=z['invalidation']):
                            result={'state':'INVALIDATED','touch_time':touch}
                        else:
                            result=confirmation_review(z,side,rows[:i+1],ti)
                            result['touch_time']=touch
                            old=prev.get('confirmation_score')
                            new=result.get('confirmation_score')
                            result['previous_confirmation_score']=old
                            if old is not None and new is not None:
                                result['score_change']=new-old
                                result['state']='STRENGTHENING' if new>old else 'WEAKENING' if new<old else 'TOUCHED'
                            if (result.get('target_times') or {}).get('major_reversal_target') is not None:
                                result['state']='MAJOR_TARGET'
                    cur.execute("INSERT INTO badang_reversal_event_514 VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",(fid,b[0],Json(result)))
                    prev=result
                    cursor=b[0]
                    if result['state'] in ('INVALIDATED','EXPIRED','DATA_GAP','MAJOR_TARGET'):
                        break
                tracked.append({'id':fid,'forecast':z,'direction':side,'latest':prev})
            for p in path.get('paths',[]):
                side=p['direction']
                for z in p['zones']:
                    # Never backdate a forecast to a candle that has already touched it.
                    if (rows[-1][3]<=z['high'] if side=='DOWN' else rows[-1][2]>=z['low']):
                        continue
                    if any(a['direction']==side and a['latest'].get('state') not in ('INVALIDATED','EXPIRED','DATA_GAP','MAJOR_TARGET') and a['forecast']['low']<=z['high'] and a['forecast']['high']>=z['low'] for a in tracked):
                        continue
                    payload=dict(z,algorithm_version='514-track-1',reference_ms=rows[-1][0])
                    fid=hashlib.sha256(json.dumps([symbol,mode,tf,side,payload['reference_ms'],z['low'],z['high']],separators=(',',':')).encode()).hexdigest()
                    cur.execute("INSERT INTO badang_reversal_forecast_514(id,symbol,mode,tf,reference_ms,direction,forecast) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",(fid,symbol,mode,tf,rows[-1][0],side,Json(payload)))
                    tracked.append({'id':fid,'forecast':payload,'direction':side,'latest':{'state':'BEFORE_TOUCH','confirmation_score':None}})
    return {'status':'SAVED','tracking_mode':'ON_SCAN','tracked':tracked}

def reversal_divergences(rows):
    """Regular and hidden divergence on confirmed price pivots, using causal indicators."""
    if len(rows)<40:
        return []
    closes=[b[4] for b in rows]
    def ema(values,p):
        out=[None]*len(values)
        if len(values)<p:return out
        v=sum(values[:p])/p
        out[p-1]=v
        for i in range(p,len(values)):
            v+=(values[i]-v)*2/(p+1)
            out[i]=v
        return out
    fast,slow=ema(closes,12),ema(closes,26)
    macd=[None if b is None else a-b for a,b in zip(fast,slow)]
    rsi=[None]*len(rows)
    changes=[b-a for a,b in zip(closes,closes[1:])]
    g=sum(max(x,0) for x in changes[:14])/14
    l=sum(max(-x,0) for x in changes[:14])/14
    for i in range(14,len(rows)):
        if i>14:
            d=changes[i-1]
            g=(13*g+max(d,0))/14
            l=(13*l+max(-d,0))/14
        rsi[i]=100*g/(g+l) if g+l else 50
    turns=confirmed_turns(rows)
    out=[]
    for kind in ('L','H'):
        pivots=[t for t in turns if t['kind']==kind]
        if len(pivots)<2:continue
        a,b=pivots[-2:]
        sign=1 if kind=='L' else -1
        if len(rows)-1-b['i']>20:continue
        if any((x[3 if sign>0 else 2]-b['price'])*sign<0 for x in rows[b['i']+1:]):continue
        dp=(b['price']-a['price'])*sign
        for name,values in (('RSI',rsi),('MACD',macd)):
            u,v=values[a['i']],values[b['i']]
            if u is None or v is None:continue
            di=(v-u)*sign
            if dp<0 and di>0:typ='REGULAR'
            elif dp>0 and di<0:typ='HIDDEN'
            else:continue
            out.append({'indicator':name,'type':typ,'side':'DOWN' if sign>0 else 'UP','price':b['price'],'pivot_time':b['time'],'confirmed_at':b['confirmed_at']})
    return out
