"""Read-only quality status for persisted REST trade snapshots. Never infer CVD coverage."""
from badang_trade_postgres_454 import status


def collection_status(symbol, now_ms=None, recent_threshold_ms=180_000):
    if not isinstance(recent_threshold_ms, int) or recent_threshold_ms <= 0:
        raise ValueError('Invalid freshness threshold')
    result = status(symbol, now_ms=now_ms)
    # Database integrity failures have no trustworthy freshness metrics.
    # Return a fail-closed diagnostic rather than raising KeyError or
    # accidentally replacing an anomaly with a healthy collection status.
    if result.get('status') == 'CLOCK_OR_RECORD_ANOMALY':
        result.update({
            'collection_status': 'CLOCK_OR_RECORD_ANOMALY',
            'quality_status': 'CLOCK_ANOMALY',
            'quality_message': '수집 기록의 시각 또는 정렬 무결성 오류',
            'continuous_collection_verified': False,
            'restart_recovery_verified': False,
            'gap_cause_verified': False,
            'poll_config_source': 'BADANG_TRADE_POLL_SECONDS',
        })
        return result
    age = result['latest_age_ms']
    result['collection_status'] = ('NO_RECORDS' if age is None else
                                   'RECENT' if 0 <= age <= recent_threshold_ms else 'STALE')
    result['coverage_confirmed'] = False
    result['is_cvd'] = False
    result['used_in_trading_score'] = False
    result['continuous_collection_verified'] = False
    from badang_trade_quality_459 import evaluate
    from badang_trade_config_460 import poll_interval_ms
    expected_ms = poll_interval_ms()
    result.update(evaluate(result, expected_poll_ms=expected_ms))
    result['poll_config_source'] = 'BADANG_TRADE_POLL_SECONDS'
    # Gaps can arise from restarts, downtime or failed polling; their cause is
    # not identifiable from snapshot timestamps alone.
    result['restart_recovery_verified'] = False
    result['gap_cause_verified'] = False
    return result
