"""Read-only, fail-closed reconciliation of existing scanner evidence.

Never upgrades a candidate, estimates probability, or places orders.
"""

def reconcile(item):
    if not isinstance(item,dict): item={}
    precision = item.get('precision_418') or item.get('signal_precision_418') or {}
    if not isinstance(precision,dict): precision={}
    # The scanner owns the actual validation object; missing evidence is NOT approval.
    direction = item.get('candidate_side')
    if direction not in ('LONG', 'SHORT'):
        direction = None
    quality = item.get('data_quality') or {}
    if not isinstance(quality,dict): quality={}
    raw_caveats=item.get('data_caveats')
    caveats=[str(c)[:160] for c in raw_caveats[:20]] if isinstance(raw_caveats,(list,tuple)) else []
    reasons = []
    if not direction:
        reasons.append('확정된 롱·숏 방향 없음')
    if item.get('exchange') != 'bitget':
        reasons.append('Bitget 단일 거래소 출처 미확인')
    venue_match=quality.get('cross_exchange')
    if venue_match is True:
        reasons.append('캔들과 파생상품의 거래소가 실제로 다름')
    elif venue_match is not False:
        caveats.append('파생상품 출처 미확인 · OI·펀딩은 진입 근거에서 제외')
    if item.get('technical_side') not in (direction,):
        reasons.append('기술적 점수 방향 불일치 또는 중립')
    if item.get('trend_aligned') is not True:
        reasons.append('기준 시간봉 추세 미정렬')
    # No claim that unavailable CVD/OI is a negative directional signal.
    unavailable = []
    if item.get('cvd_quality') != 'CONFIRMED_COMPLETE':
        unavailable.append('전체 체결 CVD 미검증')
    derivatives=item.get('futures_data_available')
    if not isinstance(derivatives,dict): derivatives={}
    if not derivatives.get('oi_history'):
        unavailable.append('OI 변화 자료 미확인')
    # An audit is deliberately advisory. The existing precision gate remains authoritative.
    precision_status = precision.get('status', 'UNVERIFIED')
    if precision_status != 'CANDIDATE':
        reasons.append('기존 확정봉 진입 검증 미통과 또는 미확인')
    decision=item.get('decision_427')
    if not isinstance(decision,dict) or decision.get('state')!='READY_REVIEW':
        reasons.append('최종 진입 판단 미통과 또는 미확인')
    return {
        'status': 'REVIEW_ONLY' if not reasons else 'WAIT',
        'direction': direction or 'NONE',
        'reasons': reasons,
        'missing_flow': unavailable,
        'caveats': caveats,
        'precision_status': precision_status,
        'probability': None,
        'order_authorized': False,
        'note': '분석 일치 여부 확인용. 체결·승률·수익 보장 아님.'
    }
