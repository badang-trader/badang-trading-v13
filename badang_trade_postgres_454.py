"""PostgreSQL persistence for audit-only Bitget REST trade snapshots.

Not a complete market trade feed, not continuous CVD, not a trading signal.
"""
import json
import time
from contextlib import closing
from badang_trade_sample_450 import parse_fills
from badang_trade_overlap_452 import audit_pair
from badang_oi_postgres_443 import _connection

SCHEMA = '''CREATE TABLE IF NOT EXISTS badang_trade_snapshots (
 symbol TEXT NOT NULL, fetched_ms BIGINT NOT NULL,
 payload JSONB NOT NULL, sample_count INTEGER NOT NULL CHECK (sample_count >= 0),
 PRIMARY KEY (symbol, fetched_ms))'''


def _rows(payload):
    return payload.get('fillList') if isinstance(payload, dict) else payload


def save_snapshot(symbol, payload, fetched_ms=None):
    """Atomic per-symbol insert with monotonic timestamps across concurrent workers."""
    now = int(time.time() * 1000)
    fetched_ms = now if fetched_ms is None else int(fetched_ms)
    if not now - 86_400_000 <= fetched_ms <= now + 60_000:
        raise ValueError('Invalid collection timestamp')
    parsed = parse_fills(payload, symbol, fetched_ms)
    symbol = parsed['symbol']
    rows = _rows(payload)
    # Explicitly disallow future timestamps in a REST snapshot.
    if parsed['sample_age_ms'] is not None and parsed['sample_age_ms'] < -60_000:
        raise ValueError('Future trade timestamps')
    with closing(_connection()) as con:
        with con:
            with con.cursor() as cur:
                cur.execute(SCHEMA)
                # Transaction-scoped advisory lock serializes inserts for the same symbol.
                cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('badang_trade_'+symbol,))
                cur.execute('SELECT fetched_ms, payload FROM badang_trade_snapshots '
                            'WHERE symbol=%s ORDER BY fetched_ms DESC LIMIT 1', (symbol,))
                previous = cur.fetchone()
                if previous and fetched_ms <= previous[0]:
                    raise ValueError('Out-of-order or duplicate collection timestamp')
                old_rows = previous[1] if previous else None
                if isinstance(old_rows, str):
                    old_rows = json.loads(old_rows)
                audit = audit_pair(old_rows, rows, symbol, previous[0], fetched_ms) if previous else None
                cur.execute('INSERT INTO badang_trade_snapshots '
                            '(symbol,fetched_ms,payload,sample_count) VALUES (%s,%s,%s::jsonb,%s)',
                            (symbol, fetched_ms, json.dumps(rows, ensure_ascii=False), parsed['sample_count']))
    return {'sample': parsed, 'overlap_audit': audit, 'stored': True,
            'source_exchange': 'bitget', 'coverage_confirmed': False,
            'is_cvd': False, 'used_in_trading_score': False}


def status(symbol, now_ms=None):
    from badang_oi_history_441 import _valid_symbol
    symbol = _valid_symbol(symbol)
    now_ms = int(time.time()*1000) if now_ms is None else int(now_ms)
    if now_ms <= 0:
        raise ValueError('Invalid observation timestamp')
    with closing(_connection()) as con:
        with con:
            with con.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute('SELECT fetched_ms FROM badang_trade_snapshots WHERE symbol=%s '
                            'ORDER BY fetched_ms DESC LIMIT 1000', (symbol,))
                times = [r[0] for r in cur.fetchall()]
    if any(type(t) is not int or t <= 0 or t > now_ms for t in times) or any(a <= b for a,b in zip(times, times[1:])):
        return {'symbol':symbol,'source_exchange':'bitget','status':'CLOCK_OR_RECORD_ANOMALY',
                'coverage_confirmed':False,'is_cvd':False,'used_in_trading_score':False,
                'warning':'수집 시각의 무결성을 확인할 수 없음'}
    gaps = [a-b for a,b in zip(times, times[1:])]
    return {'symbol':symbol,'source_exchange':'bitget','snapshot_count':len(times), 'snapshot_count_is_bounded':True,
            'snapshot_count_limit':1000, 'history_truncated_or_at_limit':len(times)>=1000,
            'latest_fetched_ms':times[0] if times else None,
            'latest_age_ms':now_ms-times[0] if times else None,
            'largest_collection_gap_ms':max(gaps) if gaps else None,
            'gap_scope':'last_1000_snapshots_only',
            'coverage_confirmed':False,'is_cvd':False,'used_in_trading_score':False,
            'warning':'REST 표본은 연속 체결 커버리지나 CVD를 보장하지 않음'}
