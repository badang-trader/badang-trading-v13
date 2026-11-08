"""Read-only, fail-closed reconciliation of existing scanner evidence.

Never upgrades a candidate, estimates probability, or places orders.
"""

def reconcile(item):
    precision = item.get('precision_418') or item.get('signal_precision_418') or {}
    # The scanner owns the actual validation object; missing evidence is NOT approval.
    direction = item.get('candidate_side')
    if direction not in ('LONG', 'SHORT'):
        direction = None
    quality = item.get('data_quality') or {}
    caveats = list(item.get('data_caveats') or [])
    reasons = []
    if not direction:
        reasons.append('확정된 롱·숏 방향 없음')
    if item.get('exchange') != 'bitget':
        reasons.append('Bitget 단일 거래소 출처 미확인')
    if quality.get('cross_exchange') is not False:
        reasons.append('캔들·파생상품 동일 거래소 확인 불가')
    if item.get('technical_side') not in (direction,):
        reasons.append('기술적 점수 방향 불일치 또는 중립')
    if item.get('trend_aligned') is not True:
        reasons.append('기준 시간봉 추세 미정렬')
    # No claim that unavailable CVD/OI is a negative directional signal.
    unavailable = []
    if item.get('cvd_quality') != 'CONFIRMED_COMPLETE':
        unavailable.append('전체 체결 CVD 미검증')
    if not (item.get('futures_data_available') or {}).get('oi_history'):
        unavailable.append('OI 변화 자료 미확인')
    # An audit is deliberately advisory. The existing precision gate remains authoritative.
    precision_status = precision.get('status', 'UNVERIFIED')
    if precision_status != 'CANDIDATE':
        reasons.append('기존 확정봉 진입 검증 미통과 또는 미확인')
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
