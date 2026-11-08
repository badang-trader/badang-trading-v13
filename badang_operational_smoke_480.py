"""Read-only collection smoke check; never proves complete fills/CVD or trading readiness.

Usage: python badang_operational_smoke_480.py
Requires passing 4.79 database preflight. Queries only existing PostgreSQL rows.
"""
import json
import time
from contextlib import closing
from badang_render_verify_479 import report


def smoke(preflight_fn=None, connect=None, now_ms=None, max_age_ms=300000):
    result = {'database_preflight_passed': False, 'snapshot_query_passed': False,
              'recent_snapshot_present': False, 'snapshot_age_ms': None,
              'sample_only': True, 'coverage_confirmed': False,
              'continuous_cvd_verified': False, 'trading_ready': False,
              'safe_to_enable_orders': False, 'read_only': True}
    try:
        if type(max_age_ms) is not int or max_age_ms <= 0:
            raise ValueError('Invalid freshness threshold')
        now = int(time.time() * 1000) if now_ms is None else now_ms
        if type(now) is not int or now <= 0:
            raise ValueError('Invalid clock')
        check = report(True) if preflight_fn is None else preflight_fn()
        if not isinstance(check, dict) or check.get('status') != 'DATABASE_PREFLIGHT_PASSED':
            result['status'] = 'PREFLIGHT_FAILED'
            return result
        result['database_preflight_passed'] = True
        if connect is None:
            from badang_oi_postgres_443 import _connection
            connect = _connection
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute('SELECT MAX(fetched_ms) FROM public.badang_trade_snapshots')
                row = cur.fetchone()
        if not isinstance(row, (tuple, list)) or len(row) != 1:
            raise ValueError('Invalid query result')
        latest = row[0]
        if latest is not None and (type(latest) is not int or latest <= 0 or latest > now):
            raise ValueError('Invalid snapshot timestamp')
        result['snapshot_query_passed'] = True
        if latest is not None:
            result['snapshot_age_ms'] = now - latest
            result['recent_snapshot_present'] = now - latest <= max_age_ms
        result['status'] = ('RECENT_SAMPLE_ONLY' if result['recent_snapshot_present']
                            else 'NO_RECENT_SAMPLE')
    except Exception:
        result['status'] = 'SNAPSHOT_QUERY_FAILED' if result['database_preflight_passed'] else 'PREFLIGHT_FAILED'
    return result


def main():
    result = smoke()
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'RECENT_SAMPLE_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
