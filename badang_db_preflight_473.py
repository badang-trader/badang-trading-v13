"""Read-only PostgreSQL preflight. No schema changes, collection, or trades.

Run: python badang_db_preflight_473.py (requires DATABASE_URL).
Prints sanitized JSON; never includes connection URL or exception details.
"""
import json
from contextlib import closing

TABLES = ('badang_trade_snapshots', 'badang_trade_worker_runs', 'badang_oi_observations')


def preflight(connect=None):
    """Verify connection and table presence without creating or altering objects."""
    if connect is None:
        from badang_oi_postgres_443 import _connection
        connect = _connection
    result = {'database_reachable': False, 'schema_ready': False,
              'read_only': True, 'live_exchange_verified': False,
              'continuous_cvd_verified': False, 'trading_ready': False}
    try:
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute('SELECT 1')
                row = cur.fetchone()
                if row != (1,):
                    raise ValueError('Unexpected connection check result')
                result['database_reachable'] = True
                present = {}
                for name in TABLES:
                    cur.execute('SELECT to_regclass(%s) IS NOT NULL', ('public.' + name,))
                    present[name] = cur.fetchone() == (True,)
                result['tables_present'] = present
                result['schema_ready'] = all(present.values())
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    return result


if __name__ == '__main__':
    print(json.dumps(preflight(), ensure_ascii=False, sort_keys=True))
