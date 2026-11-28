"""Fail-closed, read-only PostgreSQL schema compatibility check.

Run: python badang_db_schema_474.py
Passing does not establish exchange coverage, continuous CVD, or trading readiness.
"""
import json
from contextlib import closing

REQUIRED = {
    'badang_trade_snapshots': {'symbol': 'text', 'fetched_ms': 'bigint', 'payload': 'jsonb', 'sample_count': 'integer'},
    'badang_trade_worker_runs': {'run_id': 'text', 'started_ms': 'bigint', 'finished_ms': 'bigint', 'state': 'text', 'result': 'jsonb'},
    'badang_oi_observations': {'symbol': 'text', 'exchange': 'text', 'observed_ms': 'bigint', 'oi': 'double precision'},
}


def inspect_schema(connect=None):
    """Inspect public schema only, without DDL/DML; reject malformed metadata."""
    result = {'schema_compatible': False, 'read_only': True,
              'live_exchange_verified': False, 'continuous_cvd_verified': False,
              'trading_ready': False}
    try:
        if connect is None:
            from badang_oi_postgres_443 import _connection
            connect = _connection
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute('SELECT table_name, column_name, data_type FROM information_schema.columns '
                            'WHERE table_schema=%s AND table_name IN (%s,%s,%s)',
                            ('public', *REQUIRED))
                rows = cur.fetchall()
        actual = {name: {} for name in REQUIRED}
        duplicates = []
        for row in rows:
            if not isinstance(row, (tuple, list)) or len(row) != 3 or not all(isinstance(x, str) for x in row):
                raise ValueError('Invalid metadata row')
            table, column, dtype = row
            if table in actual:
                if column in actual[table]:
                    duplicates.append((table, column))
                actual[table][column] = dtype
        mismatches = {table: {column: {'expected': dtype, 'found': actual[table].get(column)}
                              for column, dtype in cols.items() if actual[table].get(column) != dtype}
                      for table, cols in REQUIRED.items()}
        result['mismatches'] = {k: v for k, v in mismatches.items() if v}
        result['duplicate_metadata'] = [{'table': t, 'column': c} for t, c in duplicates]
        result['schema_compatible'] = not result['mismatches'] and not duplicates
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    return result

if __name__ == '__main__':
    print(json.dumps(inspect_schema(), ensure_ascii=False, sort_keys=True))
