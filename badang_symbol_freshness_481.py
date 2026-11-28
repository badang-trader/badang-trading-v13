"""Read-only, per-symbol freshness check for REST fill snapshots.

Recent samples are NOT complete market coverage, CVD, or trade signals.
"""
import json
import time
from contextlib import closing
from badang_trade_job_455 import symbols_from_env
from badang_render_verify_479 import report


def check_symbols(preflight_fn=None, connect=None, symbols=None, now_ms=None, max_age_ms=300000):
    result = {'status': 'PREFLIGHT_FAILED', 'read_only': True,
              'coverage_confirmed': False, 'continuous_cvd_verified': False,
              'trading_ready': False, 'safe_to_enable_orders': False, 'symbols': []}
    try:
        if type(max_age_ms) is not int or max_age_ms <= 0:
            raise ValueError('Invalid threshold')
        now = int(time.time()*1000) if now_ms is None else now_ms
        if type(now) is not int or now <= 0:
            raise ValueError('Invalid clock')
        names = symbols_from_env() if symbols is None else symbols_from_env(','.join(symbols))
        preflight = report(True) if preflight_fn is None else preflight_fn()
        if not isinstance(preflight, dict) or preflight.get('status') != 'DATABASE_PREFLIGHT_PASSED':
            return result
        result['status'] = 'QUERY_FAILED'
        if connect is None:
            from badang_oi_postgres_443 import _connection
            connect = _connection
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute('SELECT symbol, MAX(fetched_ms) FROM public.badang_trade_snapshots '
                            'WHERE symbol = ANY(%s) GROUP BY symbol', (names,))
                rows = cur.fetchall()
        if not isinstance(rows, (list, tuple)):
            return result
        found = {}
        for row in rows:
            if not isinstance(row, (tuple, list)) or len(row) != 2:
                return result
            symbol, stamp = row
            if symbol not in names or symbol in found or type(stamp) is not int or stamp <= 0 or stamp > now:
                return result
            found[symbol] = stamp
        for symbol in names:
            stamp = found.get(symbol)
            age = now-stamp if stamp is not None else None
            result['symbols'].append({'symbol': symbol, 'latest_fetched_ms': stamp,
                 'snapshot_age_ms': age,
                 'status': 'RECENT_SAMPLE_ONLY' if age is not None and age <= max_age_ms
                           else 'NO_RECENT_SAMPLE', 'coverage_confirmed': False, 'is_cvd': False})
        result['status'] = ('ALL_RECENT_SAMPLES_ONLY' if all(s['status'] == 'RECENT_SAMPLE_ONLY' for s in result['symbols'])
                            else 'MISSING_OR_STALE_SAMPLES')
    except Exception:
        result['status'] = 'QUERY_FAILED' if result['status'] != 'PREFLIGHT_FAILED' else 'PREFLIGHT_FAILED'
        result['symbols'] = []
    return result


def main():
    outcome = check_symbols()
    print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    return 0 if outcome['status'] == 'ALL_RECENT_SAMPLES_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
