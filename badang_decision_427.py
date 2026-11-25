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
    if tf not in FRAME_MS:
        return None,'지원하지 않는 시간봉'
    if not isinstance(raw, (list, tuple)):
        return None,'OHLCV 데이터 묶음 형식 오류'
    rows=list(raw)
    if len(rows)<65: return None,'완료봉 최소 64개 필요'
    if len(rows)>5000: return None,'OHLCV 데이터 상한 초과'
    # The trailing row is disposable for legacy callers, but must still be
    # structurally valid and at the expected next candle boundary.
    trailing=rows[-1]
    if not isinstance(trailing,(list,tuple)) or len(trailing)<6:
        return None,'마지막 미확정봉 형식 오류'
    trailing_time=_f(trailing[0])
    if trailing_time is None or trailing_time<0 or not trailing_time.is_integer():
        return None,'마지막 미확정봉 시각 오류'
    # The placeholder is excluded from indicators, but reject corrupt values
    # rather than silently accepting a malformed exchange payload.
    tail_values=[_f(v) for v in trailing[1:6]]
    if (any(v is None for v in tail_values)
            or min(tail_values[:4])<=0 or tail_values[4]<0
            or tail_values[1]<max(tail_values[0],tail_values[2],tail_values[3])
            or tail_values[2]>min(tail_values[0],tail_values[3])):
        return None,'마지막 미확정봉 OHLCV 값 오류'
    bars=[]
    for r in rows[:-1]:
        if not isinstance(r, (list, tuple)) or len(r)<6:
            return None,'OHLCV 형식 누락'
        t=_f(r[0]); o,h,l,c,v=(_f(r[i]) for i in (1,2,3,4,5))
        if (t is None or t < 0 or not t.is_integer()
                or any(x is None for x in (o,h,l,c,v))
                or min(o,h,l,c)<=0 or v<0
                or h<max(o,c,l) or l>min(o,c)):
            return None,'OHLCV 값 이상'
        bars.append((int(t),o,h,l,c,v))
    step=FRAME_MS.get(tf)
    if any(bars[i][0]-bars[i-1][0]!=step for i in range(1,len(bars))):
        return None,'캔들 시간 간격 오류'
    # Contiguous timestamps alone do not prove exchange timeframe alignment.
    if any(bar[0] % step for bar in bars):
        return None,'캔들 시간봉 경계 정렬 오류'
    if int(trailing_time)!=bars[-1][0]+step:
        return None,'마지막 미확정봉 시간 간격 오류'
    # Exchange candle timestamps are bar OPEN times. A bar is confirmed only
    # after its full interval has elapsed, not merely after its open time.
    if now_ms is not None:
        now = _f(now_ms)
        if now is None or now < bars[-1][0] + step:
            return None,'마지막 분석봉이 아직 확정되지 않았거나 현재 시각 오류'
        if now - (bars[-1][0] + step) > step * 3:
            return None,'확정봉 시각이 오래됨'
        # The disposable row is the next slot, not a forecast. A timestamp
        # beyond the current candle opening indicates corrupted future data.
        if int(trailing_time) > (int(now)//step)*step:
            return None,'마지막 미확정봉 미래 시각 오류'
    return bars,'OK'

def confirmed_turns(bars,window=3):
    """Symmetric fractal pivots; confirmed_at is the OPEN timestamp of the last right-hand confirming bar.\n\n    Historical pivot time is not the time it became knowable. Backtests must\n    use confirmed_at + the candle duration, never the pivot timestamp.\n    """
    if not isinstance(window,int) or isinstance(window,bool) or window<1:
        raise ValueError('Pivot confirmation window must be a positive integer')
    turns=[]
    for i in range(window,len(bars)-window):
        hi=bars[i][2];lo=bars[i][3]
        is_hi=hi>max(b[2] for b in bars[i-window:i]) and hi>=max(b[2] for b in bars[i+1:i+window+1])
        is_lo=lo<min(b[3] for b in bars[i-window:i]) and lo<=min(b[3] for b in bars[i+1:i+window+1])
        if is_hi==is_lo:continue
        kind='H' if is_hi else 'L'; price=hi if is_hi else lo
        if turns and turns[-1]['kind']==kind:
            if (kind=='H' and price>turns[-1]['price']) or (kind=='L' and price<turns[-1]['price']):
                turns[-1]={'i':i,'time':bars[i][0], 'confirmed_at':bars[i+window][0], 'kind':kind,'price':price}
        else:turns.append({'i':i,'time':bars[i][0], 'confirmed_at':bars[i+window][0], 'kind':kind,'price':price})
    return turns

def impulse_state(turns, current, atr, as_of_open=None):
    """Assess current candidate wave number from last alternating turns; not a prediction."""
    # Never label a wave from invalid prices, volatility or untrusted pivots.
    fallback={'status':'UNDETERMINED','label':'현재 3파·5파 판별 불가',
              'alternatives':[],'note':'파동 입력값 또는 변동성 검증 불가'}
    current_value=_f(current)
    atr_value=_f(atr)
    if isinstance(current,bool) or isinstance(atr,bool):
        return fallback
    if (not isinstance(turns,(list,tuple)) or current_value is None
            or current_value<=0 or atr_value is None or atr_value<=0):
        return fallback
    if any(not isinstance(t,dict) or isinstance(t.get('price'),bool)
           or isinstance(t.get('time'),bool) or _f(t.get('price')) is None
           or _f(t.get('price'))<=0 or _f(t.get('time')) is None
           for t in turns):
        return fallback
    if any(not _f(t.get('time')).is_integer() or _f(t.get('time'))<0
           for t in turns):
        return fallback
    # Reject pivot sequences with duplicate/reversed times or an impossible
    # confirmation time. Missing confirmation remains explicitly unknown.
    if any(_f(turns[i]['time'])<=_f(turns[i-1]['time'])
           for i in range(1,len(turns))):
        return fallback
    # If the pivot detector supplies H/L types, they must alternate and
    # agree with price direction. Legacy standalone fixtures omit kind.
    kinds=[t.get('kind') for t in turns]
    if any(k is not None for k in kinds):
        if (any(k not in ('H','L') for k in kinds)
                or any(kinds[i]==kinds[i-1] for i in range(1,len(kinds)))):
            return fallback
        if any((_f(turns[i]['price'])>_f(turns[i-1]['price'])) != (kinds[i]=='H')
               for i in range(1,len(turns))):
            return fallback
    for t in turns:
        if isinstance(t.get('confirmed_at'),bool):
            return fallback
        if t.get('confirmed_at') is not None:
            confirmed=_f(t['confirmed_at'])
            if (confirmed is None or not confirmed.is_integer()
                    or confirmed<_f(t['time'])):
                return fallback
    if as_of_open is not None:
        if isinstance(as_of_open,bool):
            return fallback
        as_of=_f(as_of_open)
        if as_of is None or not as_of.is_integer() or as_of<0:
            return fallback
        # An as-of analysis cannot claim that a pivot was known unless its
        # right-hand confirmation timestamp is explicitly supplied.
        if any(t.get('confirmed_at') is None for t in turns):
            return fallback
        if any(_f(t['time'])>as_of or _f(t['confirmed_at'])>as_of
               for t in turns):
            return fallback
    turns=[dict(t,price=float(t['price']),time=int(float(t['time'])))
           for t in turns]
    current=current_value
    atr=atr_value
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
        invalid=vals[-1]
        progress=(current-invalid)*direction
        if progress<=0:continue
        # Early impulse hypotheses are not confirmed breakouts.
        previous_extreme=vals[1] if wave==3 else vals[3]
        broken=(current-previous_extreme)*direction>0
        stage='BREAKOUT_PROGRESS' if broken else 'EARLY_HYPOTHESIS'
        if wave==5 and abs(vals[3]-vals[2])<min(abs(vals[1]-vals[0]),progress):continue
        strength=progress/max(atr,1e-12)
        possibilities.append({'wave':wave,'direction':'UP' if direction>0 else 'DOWN',
                              'invalidation':round(invalid,8),'last_pivot_time':p[-1]['time'],
                              'last_pivot_confirmed_at':p[-1].get('confirmed_at'),
                              'stage':stage,'previous_extreme':previous_extreme,
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

def completed_impulse_rules(prices):
    """Validate a completed conventional five-wave impulse (six endpoints).

    This does not validate diagonals or identify wave degree. Returns reasons
    rather than converting a historical pattern into a trade recommendation.
    """
    if not isinstance(prices, (list, tuple)) or len(prices) != 6:
        return {'valid': False, 'reasons': ['6개 파동 경계점 필요']}
    vals = [_f(p) for p in prices]
    if any(v is None or v <= 0 for v in vals):
        return {'valid': False, 'reasons': ['파동 경계점 가격 오류']}
    direction = 1 if vals[1] > vals[0] else -1
    reasons = []
    if any((vals[i+1]-vals[i])*direction <= 0 for i in (0, 2, 4)):
        reasons.append('1·3·5파 진행 방향 오류')
    if any((vals[i+1]-vals[i])*direction >= 0 for i in (1, 3)):
        reasons.append('2·4파 조정 방향 오류')
    if (vals[2]-vals[0])*direction <= 0:
        reasons.append('2파가 1파 출발점을 침범')
    if (vals[4]-vals[1])*direction <= 0:
        reasons.append('일반 추진파의 4파·1파 가격 중첩')
    lengths = [abs(vals[i+1]-vals[i]) for i in (0, 2, 4)]
    if lengths[1] < min(lengths[0], lengths[2]):
        reasons.append('3파가 1·3·5파 중 최단')
    if (vals[3]-vals[1])*direction <= 0:
        reasons.append('3파가 1파 종점을 넘지 못함')
    if (vals[5]-vals[3])*direction <= 0:
        reasons.append('5파가 3파 종점을 넘지 못함: 절단 5파는 별도 시나리오')
    return {'valid': not reasons, 'reasons': reasons,
            'direction': 'UP' if direction > 0 else 'DOWN',
            'note': '일반 추진파 완성형 규칙 검사. 대각삼각형·절단파는 별도 분석 필요'}

def historical_wave_shapes(turns, tf):
    """Endpoint geometry only; subdivisions and wave degree remain unverified."""
    out=[]
    if len(turns)>=6:
        q=turns[-6:]
        p=[t['price'] for t in q]
        s=1 if p[1]>p[0] else -1
        d=[(p[i+1]-p[i])*s for i in range(5)]
        if all(d[i]>0 for i in (0,2,4)) and all(d[i]<0 for i in (1,3)):
            base=(p[2]-p[0])*s>0 and (p[3]-p[1])*s>0 and d[2]>=min(d[0],d[4])
            if base and (p[4]-p[1])*s>0:
                if (p[5]-p[3])*s<0:
                    out.append(('TRUNCATED_FIFTH_GEOMETRY',q,s))
                elif completed_impulse_rules(p)['valid']:
                    for i in (0,2,4):
                        if d[i]>=1.618*max(d[j] for j in (0,2,4) if j!=i):
                            out.append(('EXTENDED_'+str(i+1)+'_GEOMETRY',q,s))
            if base and (p[4]-p[2])*s>0 and (p[4]-p[1])*s<0 and (p[5]-p[3])*s>0:
                if d[0]>d[2]>d[4] and abs(d[1])>abs(d[3]):
                    out.append(('CONTRACTING_DIAGONAL_GEOMETRY',q,s))
                elif d[0]<d[2]<d[4] and abs(d[1])<abs(d[3]):
                    out.append(('EXPANDING_DIAGONAL_GEOMETRY',q,s))
    if len(turns)>=4:
        q=turns[-4:]
        p=[t['price'] for t in q]
        s=1 if p[1]>p[0] else -1
        a=abs(p[1]-p[0])
        if a>0 and (p[2]-p[1])*s<0 and (p[3]-p[2])*s>0:
            b=abs(p[2]-p[1])/a
            if 0<b<1 and (p[3]-p[1])*s>0:
                out.append(('ABC_ZIGZAG_GEOMETRY',q,s))
            elif .9<=b<=1.38 and (p[3]-p[1])*s>=0:
                out.append(('ABC_FLAT_GEOMETRY',q,s))
    return [{'pattern':kind,'direction':'UP' if s>0 else 'DOWN',
             'pivot_prices':[t['price'] for t in q],
             'pivot_times':[t['time'] for t in q],
             'known_at_ms':q[-1]['confirmed_at']+FRAME_MS[tf],
             'status':'HISTORICAL_GEOMETRY_ONLY','subdivision_verified':False,
             'used_in_score':False} for kind,q,s in out]

def complex_correction_geometry(turns, tf):
    """Double/triple zigzag endpoint hypotheses, not verified subdivisions."""
    results=[]
    for count,label in ((8,'WXY'),(12,'WXYXZ')):
        if len(turns)<count:
            continue
        q=turns[-count:]
        p=[t['price'] for t in q]
        s=1 if p[1]>p[0] else -1
        legs=[]
        valid=True
        for i in range(0,count-3,4):
            a=(p[i+1]-p[i])*s
            b=(p[i+1]-p[i+2])*s
            c=(p[i+3]-p[i+2])*s
            if not (a>0 and 0<b<a and c>b):
                valid=False
                break
            legs.append({'a_length':a,'b_retrace':b/a,'c_extension':c/a})
            if i+4<count:
                x=(p[i+3]-p[i+4])*s
                net=(p[i+3]-p[i])*s
                if not (0<x<net):
                    valid=False
                    break
        if valid:
            results.append({'pattern':label+'_DOUBLE_ZIGZAG_GEOMETRY' if count==8 else label+'_TRIPLE_ZIGZAG_GEOMETRY',
                            'direction':'UP' if s>0 else 'DOWN',
                            'pivot_prices':p,'pivot_times':[t['time'] for t in q],
                            'known_at_ms':q[-1]['confirmed_at']+FRAME_MS[tf],
                            'legs':legs,'status':'HISTORICAL_GEOMETRY_ONLY',
                            'subdivision_verified':False,'used_in_score':False})
    return results

def structure_review(raw,tf,now_ms=None):
    bars,reason=closed_bars(raw,tf,now_ms)
    if bars is None:return {'status':'UNAVAILABLE','reason':reason}
    recent=bars[-64:]; current=recent[-1][4]
    # Wilder ATR uses all available validated closed candles for warm-up.
    tr=[max(bars[i][2]-bars[i][3],abs(bars[i][2]-bars[i-1][4]),abs(bars[i][3]-bars[i-1][4])) for i in range(1,len(bars))]
    atr=sum(tr[:14])/14
    for value in tr[14:]:
        atr=(13*atr+value)/14
    turns=confirmed_turns(recent)
    # previous swing highs/lows only; no forward-looking values
    supports=sorted({round(t['price'],8) for t in turns if t['kind']=='L' and t['price']<current},reverse=True)
    resistances=sorted({round(t['price'],8) for t in turns if t['kind']=='H' and t['price']>current})
    wave=impulse_state(turns,current,atr,as_of_open=recent[-1][0])
    # Reject a hypothesis if any subsequent closed candle breached its origin.
    valid=[]
    for candidate in wave['alternatives']:
        sign=1 if candidate['direction']=='UP' else -1
        later=[b for b in recent if b[0]>candidate['last_pivot_time']]
        origin=candidate['invalidation']
        if any(((b[3] if sign>0 else b[2])-origin)*sign<=0 for b in later):
            continue
        p=candidate['pivot_prices']
        length=abs(p[1]-p[0])
        ratios=(1,1.618,2,2.618,4.236) if candidate['wave']==3 else (.618,1,1.272,1.618)
        targets=[]
        for ratio in ratios:
            price=p[-1]+sign*length*ratio
            if price<=0: continue
            if candidate['wave']==5 and abs(p[3]-p[2])<min(length,abs(price-p[-1])): continue
            reached=any((b[2] if sign>0 else b[3])*sign>=price*sign for b in later)
            targets.append({'price':price,'ratio':ratio,'reached':reached,'timeframe':tf,'anchor':p[-1],'length':length})
        candidate['targets']=targets
        candidate['future_targets']=[t for t in targets if not t['reached'] and (t['price']-current)*sign>0]
        candidate['reference_price']=current
        candidate['wave1_length']=length
        candidate['wave2_retrace_ratio']=abs(p[2]-p[1])/length
        candidate['structural_invalidation']=p[0] if candidate['wave']==3 else p[1]
        candidate['active_leg_invalidation']=origin
        candidate['last_pivot_confirmed_close_ms']=candidate['last_pivot_confirmed_at']+FRAME_MS[tf]
        candidate['flow_validation']={'status':'UNVERIFIED','oi_change_pct':None,'cvd':None,'used_in_score':False}
        candidate['pivot_times']=[t['time'] for t in turns[-candidate['wave']:]]
        valid.append(candidate)
    wave['alternatives']=valid
    wave['status']='AMBIGUOUS' if len(valid)>1 else 'HYPOTHESIS' if valid else 'UNDETERMINED'
    wave['label']='복수 파동 후보' if len(valid)>1 else ('상승' if valid[0]['direction']=='UP' else '하락')+' '+str(valid[0]['wave'])+'파 진행 후보' if valid else '현재 파동 미확정'

    return {'status':'OK','timeframe':tf,'last_closed_time':recent[-1][0],
            'last_closed_price':current,'atr14':round(atr,8),
            'support_levels':supports[:3], 'resistance_levels':resistances[:3],
            'swing_count':len(turns),'wave':wave,
            'historical_wave_shapes':historical_wave_shapes(turns,tf)+complex_correction_geometry(confirmed_turns(bars[-160:]),tf),
            'note':'완료봉에서 확인된 과거 스윙 레벨. 향후 지지·저항을 보장하지 않음'}

def decision_review(item,structures,mode):
    """One authoritative decision state; conservative fail closed."""
    if not isinstance(item,dict): item={}
    if not isinstance(structures,dict): structures={}
    old=item.get('decision_plan_425') or {}
    if not isinstance(old,dict): old={}
    side=old.get('side');score=_f(old.get('score'))
    raw_reasons=old.get('reasons')
    if isinstance(raw_reasons,(list,tuple)):
        reasons=[str(r)[:200] for r in raw_reasons[:30]]
    elif isinstance(raw_reasons,str):
        reasons=[raw_reasons[:200]]
    else:
        reasons=[]
    if mode not in ('scalp', 'swing'):
        return {'state':'WAIT','label':'관망 · 분석 모드 오류',
                'side':side,'score':score,'reasons':['지원하지 않는 분석 모드'],
                'wave_context':'분석 불가','plan':{},'data_is_live_quote':False,
                'win_probability':None,'note':'지원하지 않는 분석 모드에서는 진입 검토를 진행하지 않음'}
    required=('15m','30m','1H') if mode=='scalp' else ('1H','4H','1D')
    for tf in required:
        structure=structures.get(tf)
        if not isinstance(structure,dict) or structure.get('status')!='OK':
            reasons.append(tf+' 확정봉·구조 검증 불가')
    if side not in ('LONG','SHORT'):reasons.append('가격 행동 진입 방향 미확정')
    # The final decision must never resurrect a candidate rejected by the scanner.
    if 'recommendation' in item and (item.get('recommendation') != side or side not in ('LONG','SHORT')):
        reasons.append('스캔 최종 추천 방향 불일치 또는 진입 보류')
    if item.get('entry_blockers'):
        reasons.append('기존 스캔 진입 차단 사유 존재')
    if score is None or score<80:reasons.append('진입 검토 기준 80점 미달')
    rr1 = _f(old.get('rr1_net_estimate'))
    if rr1 is None or rr1 < 1.5:
        reasons.append('수수료·슬리피지 반영 손익비 1.5 미달 또는 산정 불가')
    entry, stop, tp1 = (_f(old.get(k)) for k in ('entry', 'stop', 'tp1'))
    if any(v is None or v <= 0 for v in (entry, stop, tp1)):
        reasons.append('진입·손절·1차 목표 가격 누락 또는 오류')
    elif side == 'LONG' and not (stop < entry < tp1):
        reasons.append('롱 진입·손절·목표 가격 순서 오류')
    elif side == 'SHORT' and not (tp1 < entry < stop):
        reasons.append('숏 진입·손절·목표 가격 순서 오류')
    if all(v is not None and v > 0 for v in (entry, stop, tp1)) and side in ('LONG', 'SHORT'):
        if (side == 'LONG' and stop < entry < tp1) or (side == 'SHORT' and tp1 < entry < stop):
            gross_rr = abs(tp1 - entry) / abs(entry - stop)
            # Fees and slippage cannot increase a net R:R above the gross price R:R.
            # A materially larger claimed net R:R is inconsistent with the prices.
            if rr1 is not None and rr1 > gross_rr + 1e-6:
                reasons.append('수수료·슬리피지 반영 손익비가 가격 기준 손익비보다 큼')
    # Recalculate the displayed net ratio from price geometry and stated costs.
    # A stale/mismatched net ratio must never pass the final manual-review gate.
    fee_pct = _f(old.get('fee_assumption_roundtrip_pct'))
    slip_pct = _f(old.get('slippage_assumption_roundtrip_pct'))
    # Legacy isolated decision fixtures may omit both assumptions. The live
    # scan planner always supplies both; partial declarations are invalid.
    cost_declared = ('fee_assumption_roundtrip_pct' in old or
                     'slippage_assumption_roundtrip_pct' in old)
    # Scanner-produced items must never bypass cost checks by omitting
    # both assumptions. Only legacy standalone review fixtures may omit them.
    if 'recommendation' in item and not cost_declared:
        reasons.append('스캔 비용 가정 누락 · 순손익비 검증 불가')
    if cost_declared and (fee_pct is None or slip_pct is None or
                          fee_pct < 0 or slip_pct < 0 or fee_pct + slip_pct > 5):
        reasons.append('수수료·슬리피지 가정 누락 또는 오류')
    elif cost_declared and (entry is not None and stop is not None and tp1 is not None
          and entry > 0 and stop > 0 and entry != stop and tp1 > 0):
        cost = entry * (fee_pct + slip_pct) / 100
        expected_rr1 = round(max(0, abs(tp1-entry)-cost) / (abs(entry-stop)+cost), 2)
        if rr1 is None or abs(rr1-expected_rr1) > 0.011:
            reasons.append('1차 순손익비가 수수료·슬리피지 재계산 결과와 불일치')
    tp2 = _f(old.get('tp2'))
    rr2 = _f(old.get('rr2_net_estimate'))
    if old.get('tp2') is not None:
        if tp2 is None or tp2 <= 0:
            reasons.append('2차 목표 가격 오류')
        elif all(v is not None and v > 0 for v in (entry, stop, tp1)) and side in ('LONG', 'SHORT'):
            if (side == 'LONG' and tp2 < tp1) or (side == 'SHORT' and tp2 > tp1):
                reasons.append('2차 목표가가 1차 목표보다 불리함')
    if cost_declared and (tp2 is None or tp2 <= 0):
        reasons.append('2차 목표 가격 누락 · 비용 반영 계획 검증 불가')
    if cost_declared and old.get('tp2') is not None and rr2 is None:
        reasons.append('2차 순손익비 누락 · 수수료·슬리피지 검증 불가')
    if old.get('rr2_net_estimate') is not None:
        if rr2 is None or rr2 < 0:
            reasons.append('2차 목표 손익비 오류')
        elif tp2 is not None and entry is not None and stop is not None and entry != stop:
            gross_rr2 = abs(tp2 - entry) / abs(entry - stop)
            if rr2 > gross_rr2 + 1e-6:
                reasons.append('2차 수수료·슬리피지 반영 손익비가 가격 기준 손익비보다 큼')
            if cost_declared and fee_pct is not None and slip_pct is not None and (
                    fee_pct >= 0 and slip_pct >= 0 and fee_pct + slip_pct <= 5):
                cost2 = entry * (fee_pct + slip_pct) / 100
                expected_rr2 = round(max(0, abs(tp2-entry)-cost2) /
                                     (abs(entry-stop)+cost2), 2)
                if abs(rr2-expected_rr2) > 0.011:
                    reasons.append('2차 순손익비가 수수료·슬리피지 재계산 결과와 불일치')
    if old.get('state')!='READY_REVIEW':reasons.append('기존 진입 검증 미충족')
    # A missing/invalid Elliott label is not itself a trading veto, but
    # must never be represented as a confirmed wave direction.
    # Reconcile current multi-timeframe wave ambiguity as contextual warning, not fake confidence.
    primary='15m' if mode=='scalp' else '4H'
    primary_structure=structures.get(primary)
    primary_structure=primary_structure if isinstance(primary_structure,dict) else {}
    wave=primary_structure.get('wave')
    wave=wave if isinstance(wave,dict) else {}
    wave_note=wave.get('label','파동 분석 불가')
    if not isinstance(wave_note,str): wave_note='파동 분석 불가'
    # Surface Elliott alternatives and invalidation levels as context only.
    # These hypotheses must not masquerade as independent order signals.
    wave_scenarios=[]
    if isinstance(wave.get('alternatives'),list):
        for candidate in wave['alternatives'][:5]:
            if not isinstance(candidate,dict): continue
            level=_f(candidate.get('invalidation'))
            if level is None or level<=0: continue
            direction=candidate.get('direction')
            if direction not in ('UP','DOWN'): continue
            number=candidate.get('wave')
            if type(number) is not int or number not in (3,5): continue
            wave_scenarios.append({'wave':number,'direction':direction,
                                   'invalidation':level,
                                   'last_pivot_confirmed_at':candidate.get('last_pivot_confirmed_at'),
                                   'structural_invalidation':candidate.get('structural_invalidation'),
                                   'active_leg_invalidation':candidate.get('active_leg_invalidation'),
                                   'future_targets':candidate.get('future_targets',[]),
                                   'wave2_retrace_ratio':candidate.get('wave2_retrace_ratio'),
                                   'flow_validation':candidate.get('flow_validation')})
    # Compare only independently confirmed frames; direction agreement is
    # context, not proof that lower-degree waves belong to a higher wave.
    frame_wave_context=[]
    for tf in required:
        st=structures.get(tf) or {}
        if st.get('status')!='OK':
            continue
        for w in (st.get('wave') or {}).get('alternatives',[]):
            frame_wave_context.append({'timeframe':tf,'direction':w.get('direction'),
                'wave':w.get('wave'),'stage':w.get('stage'),
                'invalidation':w.get('invalidation'),
                'known_at_ms':w.get('last_pivot_confirmed_close_ms'),
                'reference_close_ms':st['last_closed_time']+FRAME_MS[tf]})
    directions={w['direction'] for w in frame_wave_context if w['direction'] in ('UP','DOWN')}
    frame_count=len({w['timeframe'] for w in frame_wave_context})
    wave_alignment={'status':'CONFLICT' if len(directions)>1 else
        'ALIGNED_DIRECTION_ONLY' if frame_count>=2 and len(directions)==1 else 'INSUFFICIENT',
        'frames':frame_wave_context,'degree_verified':False,'used_in_score':False}
    unique=list(dict.fromkeys(reasons))
    ready=not unique
    return {'state':'READY_REVIEW' if ready else 'WAIT',
            'label':'진입 검토 가능 · 주문 전 실시간 확인' if ready else '관망 · 진입 조건 미충족',
            'side':side,'score':score,'reasons':unique,'wave_context':wave_note,
            'wave_scenarios':wave_scenarios,
            'wave_alignment':wave_alignment,
            'plan':{'entry':entry,'stop':stop,'tp1':tp1,'tp2':tp2,
                    'rr1_net_estimate':rr1,'rr2_net_estimate':rr2},
            'data_is_live_quote':False,'win_probability':None,
            'note':'확정봉 스냅샷 기반. 주문호가/청산가/실제 체결·슬리피지 미검증(가정 비용만 반영)'}
