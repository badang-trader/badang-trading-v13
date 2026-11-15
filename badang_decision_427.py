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
    if step and any(bars[i][0]-bars[i-1][0]!=step for i in range(1,len(bars))):
        return None,'캔들 시간 간격 오류'
    # Exchange candle timestamps are bar OPEN times. A bar is confirmed only
    # after its full interval has elapsed, not merely after its open time.
    if now_ms is not None:
        now = _f(now_ms)
        if now is None or now < bars[-1][0] + step:
            return None,'마지막 분석봉이 아직 확정되지 않았거나 현재 시각 오류'
        if now - (bars[-1][0] + step) > step * 3:
            return None,'확정봉 시각이 오래됨'
    return bars,'OK'

def confirmed_turns(bars,window=3):
    """Symmetric fractal pivots; confirmed_at is the OPEN timestamp of the last right-hand confirming bar.\n\n    Historical pivot time is not the time it became knowable. Backtests must\n    use confirmed_at + the candle duration, never the pivot timestamp.\n    """
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
                              'last_pivot_confirmed_at':p[-1].get('confirmed_at'),
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
                                   'last_pivot_confirmed_at':candidate.get('last_pivot_confirmed_at')})
    unique=list(dict.fromkeys(reasons))
    ready=not unique
    return {'state':'READY_REVIEW' if ready else 'WAIT',
            'label':'진입 검토 가능 · 주문 전 실시간 확인' if ready else '관망 · 진입 조건 미충족',
            'side':side,'score':score,'reasons':unique,'wave_context':wave_note,
            'wave_scenarios':wave_scenarios,
            'plan':{'entry':entry,'stop':stop,'tp1':tp1,'tp2':tp2,
                    'rr1_net_estimate':rr1,'rr2_net_estimate':rr2},
            'data_is_live_quote':False,'win_probability':None,
            'note':'확정봉 스냅샷 기반. 주문호가/청산가/실제 체결·슬리피지 미검증(가정 비용만 반영)'}
