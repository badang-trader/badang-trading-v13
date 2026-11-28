"""Heuristic Elliott candidate audit: geometry, ratios, recency, independent invalidation.
Scores are *structural fit* out of 100, not probability, backtest accuracy, or trading signal.
"""
import math

def audit_candidates(wave_result, bars, atr):
    candidates=wave_result.get('candidates') or []
    if not candidates or not bars or not atr or atr<=0:
        return {'status':'NO_AUDITABLE_CANDIDATE','ranked':[], 'note':'후보 또는 ATR 없음'}
    latest=bars[-1]['start_ms']; last_close=bars[-1]['close']
    bar_ms=max(1,bars[-1]['start_ms']-bars[-2]['start_ms']) if len(bars)>1 else 1
    ranked=[]
    for c in candidates:
        p=c['pivot_prices']; side=c['direction']; n=len(p)
        if n not in (4,6):continue
        # This pivot representation is alternating extrema, not a canonical 0-1-2-3-4-5 Elliott count.
        lengths=[abs(p[i+1]-p[i]) for i in range(n-1)]
        if min(lengths)<=0:continue
        age=max(0,round((latest-c['last_pivot_ms'])/bar_ms))
        impulse=lengths[0::2]
        retrace=lengths[1::2]
        retracement=retrace[0]/impulse[0] if retrace else None
        extension=impulse[1]/impulse[0] if len(impulse)>1 else None
        # Geometry: original code already checks successive higher/lower extremes.
        # Prefer well-formed retracements, avoid stale and very small movements.
        retrace_fit= max(0,1-abs(retracement-0.5)/0.5) if retracement is not None else 0
        ext_fit=max(0,1-abs(extension-1.618)/1.618) if extension is not None else 0
        amplitude=min(1,sum(impulse)/(max(atr,1e-12)*3))
        freshness=max(0,1-age/24)
        score=round(100*(.35*retrace_fit+.25*ext_fit+.2*amplitude+.2*freshness))
        # Candidate-specific structural level: use the penultimate corrective pivot,
        # rather than a generic last high/low; this is still a reference, not a hard Elliott invalidation.
        invalidation=p[-2]
        breached=last_close<invalidation if side=='UP' else last_close>invalidation
        ranked.append({'direction':side,'pivot_count':n,'label':c['label'],
          'structural_fit_score':score,'score_kind':'휴리스틱 구조 적합도 (승률 아님)',
          'pivot_prices':p,'last_pivot_ms':c['last_pivot_ms'],'age_bars':age,
          'retrace_ratio':round(retracement,3) if retracement is not None else None,
          'extension_ratio':round(extension,3) if extension is not None else None,
          'reference_invalidation':round(invalidation,8),'reference_breached':breached,
          'wave_count_verified':False,
          'note':'교대 스윙 전환점 기반 참고 후보. 3파/5파 실제 파동 번호 확정 아님; 중첩·파동 차수·거래량 검증 미완료.'})
    # Only recent, unbreached hypotheses are displayed. Keep exclusion counts for auditability.
    excluded={'reference_breached':0,'stale':0,'duplicate':0}
    eligible=[];seen=set()
    for item in sorted(ranked,key=lambda z:(-z['structural_fit_score'],z['age_bars'])):
        if item['reference_breached']:
            excluded['reference_breached']+=1;continue
        if item['age_bars']>24:
            excluded['stale']+=1;continue
        signature=(item['direction'],tuple(item['pivot_prices']))
        if signature in seen:
            excluded['duplicate']+=1;continue
        seen.add(signature);eligible.append(item)
    return {'status':'HEURISTIC_RANKING' if eligible else 'NO_ACTIVE_CANDIDATE',
      'ranked':eligible[:2], 'total_raw':len(ranked),'excluded':excluded,
      'note':'최근 24봉 이내의 참고 후보 최대 2개. 점수는 구조 적합도이며 승률이 아니고 3·5파 확정도 아닙니다.'}
