"""Offline, secret-safe deployment configuration check (no network, no writes).

Run: python badang_deploy_check_477.py
Exit 0 means only that local configuration is structurally plausible.
"""
import json
import os
from urllib.parse import urlsplit

from badang_trade_config_460 import poll_interval_seconds
from badang_trade_job_455 import symbols_from_env


def assess_env(env=None):
    env = os.environ if env is None else env
    result = {
        'database_url_present': False,
        'database_url_postgresql': False,
        'poll_interval_valid': False,
        'symbols_valid': False,
        'config_checks_passed': False,
        'db_connection_verified': False,
        'live_exchange_verified': False,
        'continuous_cvd_verified': False,
        'trading_ready': False,
        'read_only': True,
    }
    raw = env.get('DATABASE_URL', '')
    if isinstance(raw, str) and raw.strip():
        result['database_url_present'] = True
        try:
            parsed = urlsplit(raw.strip())
            result['database_url_postgresql'] = (parsed.scheme in ('postgresql', 'postgres')
                and bool(parsed.hostname) and bool(parsed.path.strip('/')))
        except (ValueError, TypeError):
            pass
    try:
        poll_interval_seconds(env.get('BADANG_TRADE_POLL_SECONDS', '60'))
        result['poll_interval_valid'] = True
    except (ValueError, TypeError, OverflowError):
        pass
    try:
        symbols = symbols_from_env(env.get('BADANG_TRADE_SYMBOLS', 'BTCUSDT,ETHUSDT'))
        result['symbols_valid'] = bool(symbols)
    except (ValueError, TypeError, OverflowError):
        pass
    result['config_checks_passed'] = all(result[k] for k in (
        'database_url_present', 'database_url_postgresql', 'poll_interval_valid', 'symbols_valid'))
    return result


def main():
    result = assess_env()
    print(json.dumps(result, sort_keys=True))
    return 0 if result['config_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
