"""Conservative overlap audit of consecutive REST fill samples.

Even a confirmed overlap does NOT prove complete trade coverage or CVD.
No trading signal is produced by this module.
"""
from badang_trade_sample_450 import parse_fills


def audit_pair(previous, current, symbol, previous_fetched_ms, current_fetched_ms):
    """Audit consecutive REST responses; do not infer unobserved trades."""
    if current_fetched_ms <= previous_fetched_ms:
        raise ValueError('Collection times must increase')
    old = parse_fills(previous, symbol, previous_fetched_ms)
    new = parse_fills(current, symbol, current_fetched_ms)
    def rows(value):
        return value.get('fillList') if isinstance(value, dict) else value
    a, b = rows(previous), rows(current)
    def ids(seq):
        return {str(r.get('tradeId') or r.get('id')) for r in seq}
    ids_valid = old['sample_id_integrity'] == 'IDS_PRESENT' and new['sample_id_integrity'] == 'IDS_PRESENT'
    overlap = len(ids(a) & ids(b)) if ids_valid else None
    chronological = (old['sample_last_ms'] is not None and new['sample_last_ms'] is not None
                     and new['sample_last_ms'] >= old['sample_last_ms'])
    status = ('EMPTY_SAMPLE' if not a or not b else
              'MISSING_IDS' if not ids_valid else
              'TIMESTAMP_REGRESSION' if not chronological else
              'OVERLAP_OBSERVED' if overlap else 'NO_OVERLAP_GAP_UNKNOWN')
    return {
        'symbol': old['symbol'], 'source_exchange': 'bitget',
        'status': status, 'overlap_count': overlap,
        'previous_count': old['sample_count'], 'current_count': new['sample_count'],
        'coverage_confirmed': False, 'is_cvd': False,
        'used_in_trading_score': False,
        'warning': 'REST 표본의 중첩 확인은 수집 완전성 또는 연속 CVD를 증명하지 않음',
    }
