"""Safe pre-deployment gate: offline config then read-only database checks.

Run in Render shell: python badang_predeploy_478.py
No trading orders, migrations, or exchange requests. Exit 0 means DB/config
preflight passed, NOT that trading or continuous CVD is verified.
"""
import json
from badang_deploy_check_477 import assess_env
from badang_readiness_476 import assess as assess_database


def assess(config_fn=assess_env, database_fn=assess_database):
    result = {
        'config_checks_passed': False,
        'db_checks_passed': False,
        'db_check_attempted': False,
        'predeploy_checks_passed': False,
        'live_exchange_verified': False,
        'continuous_cvd_verified': False,
        'trading_ready': False,
        'read_only': True,
    }
    try:
        config = config_fn()
        if not isinstance(config, dict) or config.get('config_checks_passed') is not True:
            result['failure_stage'] = 'configuration'
            return result
        result['config_checks_passed'] = True
    except Exception:
        result['failure_stage'] = 'configuration'
        return result
    result['db_check_attempted'] = True
    try:
        db = database_fn()
        if not isinstance(db, dict) or db.get('db_checks_passed') is not True:
            result['failure_stage'] = 'database'
            return result
        result['db_checks_passed'] = True
    except Exception:
        result['failure_stage'] = 'database'
        return result
    result['predeploy_checks_passed'] = True
    return result


def main():
    result = assess()
    print(json.dumps(result, sort_keys=True))
    return 0 if result['predeploy_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
