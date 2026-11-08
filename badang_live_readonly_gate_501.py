"""One-command, fail-closed operational smoke check. No orders or writes.

This is a diagnostic for recent REST fill *samples*, NOT a CVD or trading gate.
Run on an already deployed Render shell with DATABASE_URL configured.
"""
import json
from badang_render_verify_479 import report
from badang_storage_consistency_498 import check_consistency
from badang_worker_crosscheck_483 import crosscheck
from badang_trade_job_455 import symbols_from_env


def inspect(preflight=None, storage=None, worker=None):
    result = {'status': 'PREFLIGHT_FAILED', 'read_only': True,
              'preflight': 'NOT_RUN', 'storage': 'NOT_RUN', 'worker': 'NOT_RUN',
              'coverage_confirmed': False, 'continuous_cvd_verified': False,
              'trading_ready': False, 'safe_to_enable_orders': False}
    try:
        gate = (report(True) if preflight is None else preflight())
        if (not isinstance(gate, dict) or gate.get('status') != 'DATABASE_PREFLIGHT_PASSED'
                or gate.get('mode') != 'read_only_database'
                or gate.get('config_checks_passed') is not True
                or gate.get('db_check_attempted') is not True
                or gate.get('db_checks_passed') is not True
                or any(gate.get(k) is not False for k in ('live_exchange_verified',
                    'continuous_cvd_verified', 'trading_ready', 'safe_to_enable_orders'))):
            return result
        # Reject contradictory optional safety claims without requiring legacy
        # diagnostics to emit fields they do not currently provide.
        if gate.get('read_only', True) is not True or gate.get('coverage_confirmed', False) is not False:
            return result
        result['preflight'] = 'PASSED'
        result['status'] = 'STORAGE_FAILED'
        stored = (check_consistency() if storage is None else storage())
        if (not isinstance(stored, dict) or stored.get('status') != 'SAMPLE_COUNTS_MATCH'
                or stored.get('read_only') is not True):
            return result
        if any(stored.get(k) is not False for k in ('coverage_confirmed', 'is_cvd', 'trading_ready')):
            return result
        if (stored.get('safe_to_enable_orders', False) is not False or
                stored.get('continuous_cvd_verified', False) is not False or
                stored.get('used_in_trading_score', False) is not False):
            return result
        # A status label alone is not evidence of inspected rows.
        if (type(stored.get('checked_rows')) is not int or stored['checked_rows'] < 2
                or stored.get('missing_symbols') != []
                or stored.get('bounded_to_latest_rows') is not True
                or type(stored.get('per_symbol_limit')) is not int
                or not 1 <= stored['per_symbol_limit'] <= 1000):
            return result
        # Independently verify that every configured symbol contributed rows.
        # A total row count alone can hide a missing ETH/BTC series.
        expected = set(symbols_from_env())
        counts = stored.get('rows_per_symbol')
        inspected = stored.get('inspected_symbols')
        if (not isinstance(counts, dict) or set(counts) != expected
                or not isinstance(inspected, list) or len(inspected) != len(expected)
                or any(type(name) is not str for name in inspected)
                or set(inspected) != expected
                or any(type(n) is not int or not 1 <= n <= stored['per_symbol_limit']
                       for n in counts.values())
                or sum(counts.values()) != stored['checked_rows']):
            return result
        result['storage'] = 'SAMPLE_COUNTS_MATCH'
        result['status'] = 'WORKER_FAILED'
        checked = (crosscheck() if worker is None else worker())
        if (not isinstance(checked, dict) or checked.get('status') != 'RECENT_SAMPLES_AND_WORKER_ONLY'
                or checked.get('read_only') is not True):
            return result
        if any(checked.get(k) is not False for k in ('coverage_confirmed', 'continuous_cvd_verified',
                                                     'trading_ready', 'safe_to_enable_orders')):
            return result
        if (checked.get('is_cvd', False) is not False or
                checked.get('used_in_trading_score', False) is not False):
            return result
        # Require explicit provenance alignment, not only a success label.
        if (checked.get('latest_run_snapshot_aligned') is not True
                or checked.get('worker_status') != 'RECENT_OK'
                or checked.get('snapshot_status') != 'ALL_TWO_RECENT_SAMPLES_ONLY'):
            return result
        result['worker'] = 'RECENT_SAMPLES_AND_WORKER_ONLY'
        result['status'] = 'RECENT_REST_SAMPLES_ONLY'
    except Exception:
        # Never print exception text: DB connection strings may be present.
        result['status'] = 'CHECK_FAILED'
    return result


def main():
    result = inspect()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'RECENT_REST_SAMPLES_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
