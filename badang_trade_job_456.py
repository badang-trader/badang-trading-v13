"""Bounded retry wrapper for the audit-only trade snapshot collector.

Only network fetches are retried. Database writes are never retried blindly,
so an ambiguous commit cannot create a duplicate or misleading audit record.
"""
import json
import time
from badang_trade_job_455 import run_once, symbols_from_env


def fetch_with_retry(symbol, fetch, sleep=time.sleep, attempts=3, delay_seconds=1):
    if not isinstance(attempts, int) or not 1 <= attempts <= 5:
        raise ValueError('attempts must be between 1 and 5')
    if not isinstance(delay_seconds, (int, float)) or not 0 <= delay_seconds <= 30:
        raise ValueError('invalid retry delay')
    for index in range(attempts):
        try:
            return fetch(symbol)
        except (TimeoutError, ConnectionError):
            if index == attempts - 1:
                raise
            sleep(delay_seconds * (2 ** index))


def run_once_with_retry(symbols=None, fetch=None, save=None, clock=None,
                        sleep=time.sleep, attempts=3, delay_seconds=1):
    if fetch is None:
        from bitget_market_data import _get
        fetch = lambda symbol: _get('/api/v2/mix/market/fills', {
            'symbol': symbol, 'productType': 'USDT-FUTURES', 'limit': '100'})
    if save is None:
        from badang_trade_postgres_454 import save_snapshot
        save = save_snapshot
    # requests may raise its own timeout/connection classes. Translate only
    # known transient transport exceptions; malformed payloads must not retry.
    def bounded_fetch(symbol):
        def normalized(s):
            try:
                return fetch(s)
            except Exception as exc:
                try:
                    import requests
                    transient = (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
                except ImportError:
                    transient = ()
                if isinstance(exc, transient):
                    raise TimeoutError('Transient transport failure') from None
                raise
        return fetch_with_retry(symbol, normalized, sleep, attempts, delay_seconds)
    result = run_once(symbols, bounded_fetch, save, clock)
    result['retry_policy'] = 'fetch_only_bounded'
    return result


if __name__ == '__main__':
    outcome = run_once_with_retry()
    print(json.dumps(outcome, ensure_ascii=False))
    raise SystemExit(0 if outcome['all_ok'] else 1)
