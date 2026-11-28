"""Operator-safe verification report; never enables trading or changes the DB.

Usage: python badang_render_verify_479.py [--database]
Without --database only offline configuration is checked. With --database,
read-only DB preflight is attempted only if configuration passes.
"""
import argparse
import json
from badang_deploy_check_477 import assess_env
from badang_predeploy_478 import assess as assess_predeploy


def report(check_database=False, config_fn=assess_env, predeploy_fn=assess_predeploy):
    result = {
        'mode': 'read_only_database' if check_database else 'offline_configuration',
        'config_checks_passed': False,
        'db_check_attempted': False,
        'db_checks_passed': False,
        'live_exchange_verified': False,
        'continuous_cvd_verified': False,
        'trading_ready': False,
        'safe_to_enable_orders': False,
    }
    try:
        config = config_fn()
        result['config_checks_passed'] = isinstance(config, dict) and config.get('config_checks_passed') is True
        if not result['config_checks_passed']:
            result['status'] = 'CONFIGURATION_FAILED'
            return result
        if not check_database:
            result['status'] = 'CONFIGURATION_ONLY_PASSED'
            return result
        checked = predeploy_fn()
        if not isinstance(checked, dict):
            result['status'] = 'DATABASE_FAILED'
            return result
        result['db_check_attempted'] = checked.get('db_check_attempted') is True
        result['db_checks_passed'] = checked.get('db_checks_passed') is True
        result['status'] = 'DATABASE_PREFLIGHT_PASSED' if (result['db_check_attempted'] and result['db_checks_passed'] and checked.get('predeploy_checks_passed') is True) else 'DATABASE_FAILED'
        return result
    except Exception:
        result['status'] = 'DATABASE_FAILED' if check_database and result['config_checks_passed'] else 'CONFIGURATION_FAILED'
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Safe BADANG Render verification; never enables trading')
    parser.add_argument('--database', action='store_true', help='Attempt read-only PostgreSQL checks after config checks')
    args = parser.parse_args(argv)
    result = report(check_database=args.database)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] in ('CONFIGURATION_ONLY_PASSED', 'DATABASE_PREFLIGHT_PASSED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
