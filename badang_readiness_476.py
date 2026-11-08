"""Fail-closed, read-only deployment readiness gate.

Usage: python badang_readiness_476.py
Exit 0 only for DB checks passing; NEVER implies trading readiness.
"""
import json
from badang_db_preflight_473 import preflight, TABLES
from badang_db_schema_474 import inspect_schema


def assess(preflight_fn=preflight, schema_fn=inspect_schema):
    """Run independent checks; only allowlisted booleans leave this boundary."""
    result = {'database_reachable': False, 'tables_present': False,
              'schema_compatible': False, 'db_checks_passed': False,
              'live_exchange_verified': False, 'continuous_cvd_verified': False,
              'trading_ready': False, 'read_only': True}
    try:
        p = preflight_fn()
        if not isinstance(p, dict):
            raise ValueError('Invalid preflight result')
        result['database_reachable'] = p.get('database_reachable') is True
        tables = p.get('tables_present')
        result['tables_present'] = (isinstance(tables, dict) and set(tables) == set(TABLES)
                                    and all(tables[name] is True for name in TABLES)
                                    and p.get('schema_ready') is True)
    except Exception:
        result['preflight_error'] = True
    try:
        s = schema_fn()
        if not isinstance(s, dict):
            raise ValueError('Invalid schema result')
        result['schema_compatible'] = s.get('schema_compatible') is True
    except Exception:
        result['schema_error'] = True
    result['db_checks_passed'] = all(result[k] for k in
                                     ('database_reachable', 'tables_present', 'schema_compatible'))
    return result


def main():
    result = assess()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['db_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
