"""Read-only worker restart evidence, distinct from trade coverage or recovery proof."""


def diagnose_restart(rows, now_ms, stale_after_ms):
    """Rows newest-first: (started_ms, finished_ms, state).

    A later run after an unfinished run establishes *a later attempt*, not
    successful backfill, restart cause, or uninterrupted execution.
    """
    if type(now_ms) is not int or now_ms <= 0 or type(stale_after_ms) is not int or stale_after_ms <= 0:
        raise ValueError('Invalid clock or threshold')
    if not isinstance(rows, (list, tuple)):
        raise ValueError('Invalid run history')
    previous_start = None
    interrupted = 0
    latest = None
    for index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError('Invalid audit row')
        start, finish, state = row
        if type(start) is not int or start <= 0 or start > now_ms or (previous_start is not None and start > previous_start):
            raise ValueError('Invalid audit chronology')
        if state not in ('running', 'ok', 'failed'):
            raise ValueError('Invalid audit state')
        if state == 'running':
            if finish is not None:
                raise ValueError('Running row cannot be finished')
            if index > 0:
                interrupted += 1
        elif type(finish) is not int or finish < start or finish > now_ms:
            raise ValueError('Invalid finish time')
        if index == 0:
            latest = (start, finish, state)
        previous_start = start
    if not rows:
        status = 'NO_HISTORY'
    elif interrupted:
        status = 'PREVIOUS_UNFINISHED_RUN'
    elif latest[2] == 'running' and now_ms - latest[0] > stale_after_ms:
        status = 'LATEST_RUN_OVERDUE'
    elif latest[2] == 'failed':
        status = 'LATEST_FAILED'
    else:
        status = 'NO_INTERRUPTION_EVIDENCE'
    return {
        'status': status, 'previous_unfinished_runs': interrupted,
        'later_run_observed': bool(interrupted),
        'restart_cause_known': False, 'backfill_verified': False,
        'coverage_confirmed': False, 'is_cvd': False,
        'used_in_trading_score': False,
    }


def latest_recovery(now_ms=None, connect=None, limit=25):
    """Read audit history from PostgreSQL; bounded, read-only status."""
    import time
    from contextlib import closing
    from badang_trade_config_460 import poll_interval_seconds
    from badang_trade_runs_461 import SCHEMA
    if connect is None:
        from badang_oi_postgres_443 import _connection
        connect = _connection
    if type(limit) is not int or not 2 <= limit <= 100:
        raise ValueError('Invalid history limit')
    now_ms = int(time.time()*1000) if now_ms is None else now_ms
    with closing(connect()) as con:
        with con.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute('SELECT started_ms,finished_ms,state FROM badang_trade_worker_runs '
                        'ORDER BY started_ms DESC LIMIT %s', (limit,))
            rows = cur.fetchall()
    result = diagnose_restart(rows, now_ms, poll_interval_seconds()*3000)
    result['inspected_runs'] = len(rows)
    result['history_limited'] = len(rows) == limit
    return result
