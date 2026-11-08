"""BADANG 4.27: explainable closed-candle structure and wave-state hypotheses.
No trading execution, no win-rate claims. All levels derived from validated historical candles.
"""
import math

FRAME_MS={'5m':300000,'15m':900000,'30m':1800000,'1H':3600000,'2H':7200000,'4H':14400000,'1D':86400000}

def _f(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError,OverflowError): return None

def closed_bars(raw, tf, now_ms=None):
    """Exclude last possibly-forming bar, verify time ordering and age."""
    rows=list(raw or [])
    if len(rows)<65: return None,'완료봉 최소 64개 필요'
    bars=[]
    for r in rows[:-1]:
        if len(r)<6: return None,'OHLCV 형식 누락'
        t=_f(r[0]); o,h,l,c,v=(_f(r[i]) for i in (1,2,3,4,5))
        if any(x is None for x in (t,o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c):
            return None,'OHLCV 값 이상'
        bars.append((int(t),o,h,l,c,v))
    step=FRAME_MS.get(tf)
    if step and any(bars[i][0]-bars[i-1][0]!=step for i in range(1,len(bars))):
        return None,'캔들 시간 간격 오류'
    if now_ms is not None and step and (now_ms-bars[-1][0]>step*3 or now_ms-bars[-1][0]<0):
        return None,'확정봉 시각이 오래되었거나 미래임'
    return bars,'OK'

def confirmed_turns(bars,window=3):
    """Symmetric fractal pivots; last window candles cannot confirm a turn."""
    turns=[]
    for i in range(window,len(bars)-window):
        hi=bars[i][2];lo=bars[i][3]
        is_hi=hi>max(b[2] for b in bars[i-window:i]) and hi>=max(b[2] for b in bars[i+1:i+window+1])
        is_lo=lo<min(b[3] for b in bars[i-window:i]) and lo<=min(b[3] for b in bars[i+1:i+window+1])
        if is_hi==is_lo:continue
        kind='H' if is_hi else 'L'; price=hi if is_hi else lo
        if turns and turns[-1]['kind']==kind:
            if (kind=='H' and price>turns[-1]['price']) or (kind=='L' and price<turns[-1]['price']):
                turns[-1]={'i':i,'time':bars[i][0],'kind':kind,'price':price}
        else:turns.append({'i':i,'time':bars[i][0],'kind':kind,'price':price})
    return turns

def impulse_state(turns, current, atr):
    """Assess current candidate wave number from last alternating turns; not a prediction."""
    possibilities=[]
    # 0,1,2 -> possible active 3; 0..2,3,4 -> possible active 5
    for count,wave in ((3,3),(5,5)):
        if len(turns)<count:continue
        p=turns[-count:]
        direction=1 if p[1]['price']>p[0]['price'] else -1
        vals=[x['price'] for x in p]
        if any((vals[i+1]-vals[i])*direction<=0 for i in range(0,count-1,2)):continue
        if any((vals[i+1]-vals[i])*direction>=0 for i in range(1,count-1,2)):continue
        if (vals[2]-vals[0])*direction<=0:continue
        if count==5:
            if (vals[3]-vals[1])*direction<=0:continue
            if (vals[4]-vals[1])*direction<=0:continue # conventional non-overlap
            if abs(vals[3]-vals[2])<abs(vals[1]-vals[0])*.35:continue
        invalid=vals[-1]
        progress=(current-invalid)*direction
        if progress<=0:continue
        # Wave 3 requires advance past wave1 extreme to be labelled 3-progress.
        if wave==3 and (current-vals[1])*direction<=0:continue
        if wave==5 and (current-vals[3])*direction<=0:continue
        strength=progress/max(atr,1e-12)
        possibilities.append({'wave':wave,'direction':'UP' if direction>0 else 'DOWN',
                              'invalidation':round(invalid,8),'last_pivot_time':p[-1]['time'],
                              'atr_progress':round(strength,2),'pivot_prices':[round(v,8) for v in vals]})
    if not possibilities:return {'status':'UNDETERMINED','label':'현재 3파·5파 판별 불가','alternatives':[],
                                 'note':'최근 확정 전환점이 일반 추진파 규칙을 충족하지 않음'}
    # Multiple compatible counts are ambiguity, not certainty.
    possibilities.sort(key=lambda x:(x['last_pivot_time'],x['wave']),reverse=True)
    if len(possibilities)>1:
        return {'status':'AMBIGUOUS','label':'3파·5파 복수 시나리오','alternatives':possibilities,
                'note':'파동 차수 중첩 가능성. 단일 파동 확정 불가'}
    p=possibilities[0]
    return {'status':'HYPOTHESIS','label':f"{p['direction']=='UP' and '상승' or '하락'} {p['wave']}파 진행 후보",
            'alternatives':possibilities,'note':'확정 전환점 기반 가설. 파동 완료·승률·주문 신호가 아님'}

def structure_review(raw,tf,now_ms=None):
    bars,reason=closed_bars(raw,tf,now_ms)
    if bars is None:return {'status':'UNAVAILABLE','reason':reason}
    recent=bars[-64:]; current=recent[-1][4]
    tr=[max(recent[i][2]-recent[i][3],abs(recent[i][2]-recent[i-1][4]),abs(recent[i][3]-recent[i-1][4])) for i in range(1,len(recent))]
    atr=sum(tr[-14:])/14
    turns=confirmed_turns(recent)
    # previous swing highs/lows only; no forward-looking values
    supports=sorted({round(t['price'],8) for t in turns if t['kind']=='L' and t['price']<current},reverse=True)
    resistances=sorted({round(t['price'],8) for t in turns if t['kind']=='H' and t['price']>current})
    wave=impulse_state(turns,current,atr)
    return {'status':'OK','timeframe':tf,'last_closed_time':recent[-1][0],
            'last_closed_price':current,'atr14':round(atr,8),
            'support_levels':supports[:3], 'resistance_levels':resistances[:3],
            'swing_count':len(turns),'wave':wave,
            'note':'완료봉에서 확인된 과거 스윙 레벨. 향후 지지·저항을 보장하지 않음'}

def decision_review(item,structures,mode):
    """One authoritative decision state; conservative fail closed."""
    old=item.get('decision_plan_425') or {}
    side=old.get('side');score=_f(old.get('score'))
    reasons=list(old.get('reasons') or [])
    required=('15m','30m','1H') if mode=='scalp' else ('1H','4H','1D')
    for tf in required:
        if structures.get(tf,{}).get('status')!='OK':reasons.append(tf+' 확정봉·구조 검증 불가')
    if side not in ('LONG','SHORT'):reasons.append('가격 행동 진입 방향 미확정')
    if score is None or score<80:reasons.append('진입 검토 기준 80점 미달')
    if old.get('rr1_net_estimate') is None or old.get('rr1_net_estimate')<1.5:
        reasons.append('수수료 반영 손익비 1.5 미달 또는 산정 불가')
    if old.get('state')!='READY_REVIEW':reasons.append('기존 진입 검증 미충족')
    # Reconcile current multi-timeframe wave ambiguity as contextual warning, not fake confidence.
    primary='15m' if mode=='scalp' else '4H'
    wave=structures.get(primary,{}).get('wave') or {}
    wave_note=wave.get('label','파동 분석 불가')
    unique=list(dict.fromkeys(reasons))
    ready=not unique
    return {'state':'READY_REVIEW' if ready else 'WAIT',
            'label':'진입 검토 가능 · 주문 전 실시간 확인' if ready else '관망 · 진입 조건 미충족',
            'side':side,'score':score,'reasons':unique,'wave_context':wave_note,
            'plan':{'entry':old.get('entry'),'stop':old.get('stop'),'tp1':old.get('tp1'),'tp2':old.get('tp2'),
                    'rr1_net_estimate':old.get('rr1_net_estimate'),'rr2_net_estimate':old.get('rr2_net_estimate')},
            'data_is_live_quote':False,'win_probability':None,
            'note':'확정봉 스냅샷 기반. 주문호가/청산가/체결·슬리피지 미반영'}
