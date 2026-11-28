"""Audit-only worker cycle lifecycle in PostgreSQL; not proof of fill coverage."""
import json
import time
import uuid
from contextlib import closing

SCHEMA = '''CREATE TABLE IF NOT EXISTS badang_trade_worker_runs (
 run_id TEXT PRIMARY KEY, started_ms BIGINT NOT NULL,
 finished_ms BIGINT, state TEXT NOT NULL CHECK (state IN ('running','ok','failed')),
 result JSONB, CHECK (finished_ms IS NULL OR finished_ms >= started_ms))'''


def record_start(run_id=None, started_ms=None, connect=None):
    from badang_oi_postgres_443 import _connection
    connect = _connection if connect is None else connect
    run_id = str(uuid.uuid4()) if run_id is None else str(uuid.UUID(str(run_id)))
    started_ms = int(time.time()*1000) if started_ms is None else int(started_ms)
    if started_ms <= 0:
        raise ValueError('Invalid start timestamp')
    with closing(connect()) as con:
        with con:
            with con.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute('INSERT INTO badang_trade_worker_runs (run_id,started_ms,state) VALUES (%s,%s,%s)',
                            (run_id, started_ms, 'running'))
    return run_id


def record_finish(run_id, all_ok, finished_ms=None, connect=None):
    from badang_oi_postgres_443 import _connection
    connect = _connection if connect is None else connect
    run_id = str(uuid.UUID(str(run_id)))
    finished_ms = int(time.time()*1000) if finished_ms is None else int(finished_ms)
    state = 'ok' if all_ok is True else 'failed'
    with closing(connect()) as con:
        with con:
            with con.cursor() as cur:
                cur.execute('UPDATE badang_trade_worker_runs SET finished_ms=%s,state=%s '
                            'WHERE run_id=%s AND state=%s AND started_ms<=%s',
                            (finished_ms, state, run_id, 'running', finished_ms))
                if cur.rowcount != 1:
                    raise ValueError('Run missing, already finished, or invalid finish timestamp')
    return state


def assess_runs(rows, now_ms, stale_after_ms):
    """Fail-closed diagnosis of newest-first runs; never proves trade coverage."""
    if type(now_ms) is not int or now_ms <= 0 or type(stale_after_ms) is not int or stale_after_ms <= 0:
        raise ValueError('Invalid clock or stale threshold')
    base = {'restart_verified': False, 'coverage_confirmed': False,
            'is_cvd': False, 'used_in_trading_score': False}
    if not rows:
        return {**base, 'status': 'NO_RUNS', 'historical_unfinished_count': 0}
    valid = True
    previous_start = None
    unfinished = 0
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            valid = False
            break
        start, finish, state = row
        if type(start) is not int or start <= 0 or start > now_ms:
            valid = False
        if finish is not None and (type(finish) is not int or finish < start or finish > now_ms):
            valid = False
        if state not in ('running', 'ok', 'failed'):
            valid = False
        if (state == 'running') != (finish is None):
            valid = False
        if previous_start is not None and start >= previous_start:
            valid = False
        if state == 'running':
            unfinished += 1
        previous_start = start
    if not valid:
        first = rows[0]
        future_start = (isinstance(first, (tuple, list)) and len(first) == 3
                        and type(first[0]) is int and first[0] > now_ms)
        return {**base, 'status': ('CLOCK_ANOMALY' if future_start else 'CLOCK_OR_RECORD_ANOMALY'),
                'historical_unfinished_count': unfinished}
    start, finish, state = rows[0]
    if state == 'running':
        status = 'INTERRUPTED_OR_RUNNING' if now_ms-start > stale_after_ms else 'RUNNING'
    elif state == 'failed':
        status = 'FAILED'
    else:
        status = 'STALE' if now_ms-finish > stale_after_ms else 'RECENT_OK'
    return {**base, 'status': status, 'latest_started_ms': start,
            'latest_finished_ms': finish,
            'historical_unfinished_count': unfinished,
            'previous_run_unfinished': any(row[2] == 'running' for row in rows[1:]),
            'warning': '수집 재개는 체결 누락 복구 또는 연속 CVD 검증을 의미하지 않음'}

def latest_status(now_ms=None, connect=None):
    from badang_oi_postgres_443 import _connection
    from badang_trade_config_460 import poll_interval_seconds
    connect = _connection if connect is None else connect
    now_ms = int(time.time()*1000) if now_ms is None else int(now_ms)
    with closing(connect()) as con:
        with con:
            with con.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute('SELECT started_ms,finished_ms,state FROM badang_trade_worker_runs '
                            'ORDER BY started_ms DESC LIMIT 20')
                rows = cur.fetchall()
    return assess_runs(rows, now_ms, poll_interval_seconds()*3000)
