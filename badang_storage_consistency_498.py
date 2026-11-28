"""Read-only verification of recent stored snapshot counts, not trade coverage."""
import json
import time
from contextlib import closing

SQL = ('SELECT symbol, fetched_ms, payload, sample_count FROM ('
       'SELECT symbol, fetched_ms, payload, sample_count, '
       'ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY fetched_ms DESC) AS rn '
       'FROM public.badang_trade_snapshots WHERE symbol = ANY(%s)'
       ') AS ranked WHERE rn <= %s ORDER BY symbol, fetched_ms DESC')


def check_consistency(connect=None, symbols=None, limit=200, now_ms=None):
    """Fail closed on malformed DB records; never expose payloads or credentials."""
    result = {'status': 'QUERY_FAILED', 'read_only': True,
              'coverage_confirmed': False, 'is_cvd': False,
              'trading_ready': False, 'checked_rows': 0, 'missing_symbols': [],
              'inspected_symbols': [], 'rows_per_symbol': {}}
    try:
        from badang_trade_job_455 import symbols_from_env
        names = symbols_from_env() if symbols is None else symbols_from_env(','.join(symbols))
        if type(limit) is not int or not 1 <= limit <= 1000:
            return result
        if connect is None:
            from badang_oi_postgres_443 import _connection
            connect = _connection
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute(SQL, (names, limit))
                rows = cur.fetchall()
        if not isinstance(rows, (tuple, list)):
            return result
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        if type(now_ms) is not int or now_ms <= 0:
            return result
        seen = set()
        last_stamp = {}
        for row in rows:
            if not isinstance(row, (tuple, list)) or len(row) != 4:
                return result
            symbol, stamp, payload, count = row
            if (symbol not in names or type(stamp) is not int or stamp <= 0 or
                    stamp > now_ms or (symbol, stamp) in seen or
                    (symbol in last_stamp and stamp >= last_stamp[symbol])):
                result['status'] = 'RECORD_ANOMALY'
                return result
            seen.add((symbol, stamp))
            last_stamp[symbol] = stamp
            if isinstance(payload, str):
                payload = json.loads(payload)
            if (not isinstance(payload, list) or type(count) is not int or
                    count != len(payload) or count < 0 or count > 100):
                result['status'] = 'COUNT_MISMATCH'
                return result
            result['checked_rows'] += 1
        counts = {name: 0 for name in names}
        for symbol, _ in seen:
            counts[symbol] += 1
        result['inspected_symbols'] = sorted(name for name, count in counts.items() if count)
        result['rows_per_symbol'] = counts
        missing = sorted(set(names) - {symbol for symbol, _ in seen})
        result['missing_symbols'] = missing
        result['status'] = ('NO_SNAPSHOTS' if not rows else
                            'MISSING_SYMBOLS' if missing else 'SAMPLE_COUNTS_MATCH')
        result['bounded_to_latest_rows'] = True
        result['per_symbol_limit'] = limit
    except Exception:
        result['status'] = 'QUERY_FAILED'
    return result


def main():
    result = check_consistency()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'SAMPLE_COUNTS_MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
