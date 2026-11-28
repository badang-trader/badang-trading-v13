"""One-shot audit-only Bitget REST trade snapshot job.

Invoke via an external scheduler; this does not establish complete market coverage.
"""
import json
import os
import time
from badang_oi_history_441 import _valid_symbol


def symbols_from_env(raw=None):
    raw = os.getenv('BADANG_TRADE_SYMBOLS', 'BTCUSDT,ETHUSDT') if raw is None else raw
    parts = [s.strip().upper() for s in raw.split(',')]
    if not parts or any(not p for p in parts) or len(parts) > 20:
        raise ValueError('Invalid symbol list')
    symbols = [_valid_symbol(p) for p in parts]
    if len(set(symbols)) != len(symbols):
        raise ValueError('Duplicate symbols')
    return symbols


def run_once(symbols=None, fetch=None, save=None, clock=None):
    # Dependency injection keeps the scheduler testable without Bitget or PostgreSQL.
    if fetch is None:
        from bitget_market_data import _get
        fetch = lambda symbol: _get('/api/v2/mix/market/fills', {
            'symbol': symbol, 'productType': 'USDT-FUTURES', 'limit': '100'})
    if save is None:
        from badang_trade_postgres_454 import save_snapshot
        save = save_snapshot
    if clock is None:
        clock = lambda: int(time.time() * 1000)
    symbols = symbols_from_env() if symbols is None else symbols_from_env(','.join(symbols))
    results = []
    for symbol in symbols:
        try:
            # Timestamp taken after the fetch, not before network latency.
            payload = fetch(symbol)
            result = save(symbol, payload, fetched_ms=clock())
            # Reject malformed storage acknowledgements: they are not proof of a saved sample.
            if not isinstance(result, dict) or not isinstance(result.get('sample'), dict):
                raise ValueError('Invalid snapshot storage acknowledgement')
            # A sample count alone does not prove that PostgreSQL committed it.
            if result.get('stored') is not True:
                raise ValueError('Snapshot was not confirmed stored')
            if (result.get('coverage_confirmed') is not False or
                    result.get('is_cvd') is not False or
                    result.get('used_in_trading_score') is not False):
                raise ValueError('Unsafe snapshot readiness claim')
            if result['sample'].get('symbol') != symbol:
                raise ValueError('Stored snapshot symbol mismatch')
            count = result['sample'].get('sample_count')
            if type(count) is not int or count < 0 or count > 100:
                raise ValueError('Invalid snapshot sample count')
            results.append({'symbol': symbol, 'ok': True,
                            'sample_count': count,
                            'coverage_confirmed': False, 'is_cvd': False})
        except Exception as exc:
            # Do not log payload, API credentials, or DATABASE_URL.
            results.append({'symbol': symbol, 'ok': False,
                            'error_type': type(exc).__name__,
                            'coverage_confirmed': False, 'is_cvd': False})
    return {'results': results, 'all_ok': all(r['ok'] for r in results),
            'coverage_confirmed': False, 'is_cvd': False}


if __name__ == '__main__':
    outcome = run_once()
    print(json.dumps(outcome, ensure_ascii=False))
    raise SystemExit(0 if outcome['all_ok'] else 1)
