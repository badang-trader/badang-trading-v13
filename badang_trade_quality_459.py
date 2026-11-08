"""Conservative quality checks for REST snapshots; never establishes trade completeness."""

def evaluate(status, expected_poll_ms=60_000, gap_multiplier=2):
    if type(expected_poll_ms) is not int or not 15_000 <= expected_poll_ms <= 3_600_000:
        raise ValueError('Invalid expected polling interval')
    if type(gap_multiplier) is not int or not 2 <= gap_multiplier <= 10:
        raise ValueError('Invalid gap multiplier')
    count = status.get('snapshot_count')
    age = status.get('latest_age_ms')
    gap = status.get('largest_collection_gap_ms')
    if type(count) is not int or count < 0:
        raise ValueError('Invalid snapshot count')
    if age is not None and (type(age) is not int or age < 0):
        return _result('CLOCK_ANOMALY', '수집 시각이 현재 시각보다 미래임', expected_poll_ms)
    if gap is not None and (type(gap) is not int or gap < 0):
        return _result('CLOCK_ANOMALY', '수집 간격 값이 유효하지 않음', expected_poll_ms)
    if count == 0:
        return _result('NO_RECORDS', '저장된 체결 표본 없음', expected_poll_ms)
    if age is None:
        return _result('CLOCK_ANOMALY', '마지막 수집 시각 누락', expected_poll_ms)
    if age > expected_poll_ms * gap_multiplier:
        return _result('STALE', '최근 수집이 지연됨', expected_poll_ms)
    if count < 2:
        return _result('INSUFFICIENT_HISTORY', '수집 기록이 1회뿐임', expected_poll_ms)
    if gap is None:
        return _result('INSUFFICIENT_HISTORY', '수집 간격을 확인할 수 없음', expected_poll_ms)
    if gap > expected_poll_ms * gap_multiplier:
        return _result('GAP_DETECTED', '저장된 표본 사이에 수집 간격 초과 발견', expected_poll_ms)
    return _result('SNAPSHOTS_REGULAR', '최근 저장 시각은 일정하지만 개별 체결 누락 여부는 알 수 없음', expected_poll_ms)


def _result(code, message, expected):
    return {'quality_status': code, 'quality_message': message,
            'expected_poll_ms': expected, 'coverage_confirmed': False,
            'continuous_collection_verified': False, 'is_cvd': False,
            'used_in_trading_score': False}
