"""One-shot OI collection job for an external scheduler (not a background web thread).

Requires DATABASE_URL. Run every 1-5 minutes using a managed cron job.
This is not CVD and does not enable trading signals.
"""
import argparse
import json
import os
import sys
import time
from badang_oi_history_441 import _valid_symbol

DEFAULT_SYMBOLS = ('BTCUSDT', 'ETHUSDT')


def parse_symbols(raw):
    parts = [part.strip().upper() for part in raw.split(',')]
    if not parts or len(parts) > 20 or any(not part for part in parts):
        raise ValueError('Specify 1 to 20 comma-separated symbols')
    symbols = []
    for part in parts:
        symbol = _valid_symbol(part)
        if symbol not in symbols:
            symbols.append(symbol)
    return symbols


def collect_once(symbols, observer=None, pause_seconds=0.2):
    if observer is None:
        from badang_oi_postgres_443 import observe
        observer = observe
    results = []
    for i, symbol in enumerate(symbols):
        if i and pause_seconds:
            time.sleep(pause_seconds)
        try:
            value = observer(symbol)
            results.append({'symbol': symbol, 'ok': True,
                            'status': value.get('status', 'UNKNOWN')})
        except Exception as exc:
            # Do not expose credentials, connection strings or full HTTP errors.
            results.append({'symbol': symbol, 'ok': False,
                            'error_type': type(exc).__name__})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='One-shot Bitget OI collector')
    parser.add_argument('--symbols', default=os.getenv('BADANG_OI_SYMBOLS', ','.join(DEFAULT_SYMBOLS)))
    args = parser.parse_args(argv)
    try:
        symbols = parse_symbols(args.symbols)
    except ValueError as exc:
        parser.error(str(exc))
    if not os.getenv('DATABASE_URL', '').strip():
        print(json.dumps({'error': 'DATABASE_URL_REQUIRED'}))
        return 2
    results = collect_once(symbols)
    print(json.dumps({'collected_at_ms': int(time.time() * 1000),
                      'results': results}, ensure_ascii=False))
    return 0 if all(r['ok'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
