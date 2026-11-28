"""Single-process periodic audit snapshot runner, NOT a continuous trade feed.

Run as a dedicated Render worker (not inside gunicorn). Multiple replicas can
produce overlapping snapshots; database constraints still enforce timestamps.
"""
import json
import os
import signal
import threading
import time
from badang_trade_job_456 import run_once_with_retry


def interval_from_env(raw=None):
    from badang_trade_config_460 import poll_interval_seconds
    return poll_interval_seconds(raw)


READINESS_FLAGS = ('coverage_confirmed', 'is_cvd', 'continuous_cvd_verified',
                   'trading_ready', 'safe_to_enable_orders')


def _reject_unverified_claims(record):
    """Explicit readiness fields may only contain the boolean False.

    Reject truthy strings, numbers and nulls rather than silently treating them
    as safe; external callers can otherwise misinterpret a non-boolean claim.
    """
    if any(name in record and record[name] is not False for name in READINESS_FLAGS):
        raise ValueError('Unsupported collection readiness claim')


def safe_cycle_outcome(outcome, expected_symbols=None, require_nonempty=False):
    """Validate worker success claims and emit only a credential-safe summary."""
    if (not isinstance(outcome, dict) or type(outcome.get('all_ok')) is not bool
            or not isinstance(outcome.get('results'), list)):
        raise ValueError('Invalid collection result')
    _reject_unverified_claims(outcome)
    # all([]) is True: never report an empty collection cycle as successful.
    if require_nonempty and not outcome['results']:
        raise ValueError('Empty collection results')
    clean = []
    seen = set()
    for item in outcome['results']:
        if (not isinstance(item, dict) or type(item.get('ok')) is not bool
                or not isinstance(item.get('symbol'), str)
                or not item['symbol'].isascii() or not item['symbol'].isalnum()
                or len(item['symbol']) > 30
                ):
            raise ValueError('Invalid symbol collection result')
        _reject_unverified_claims(item)
        if item['symbol'] in seen:
            raise ValueError('Duplicate collection symbol')
        seen.add(item['symbol'])
        clean.append({'symbol': item['symbol'], 'ok': item['ok']})
    if expected_symbols is not None:
        from badang_trade_job_455 import symbols_from_env
        expected = symbols_from_env(','.join(expected_symbols))
        if seen != set(expected):
            raise ValueError('Collection symbol set mismatch')
    if outcome['all_ok'] != all(item['ok'] for item in clean):
        raise ValueError('Inconsistent collection success claim')
    return {'all_ok': outcome['all_ok'], 'results': clean}


def run_periodic(run=None, interval=None, stop=None, clock=None, wait=None, max_cycles=None, emit=None, audit_start=None, audit_finish=None, expected_symbols=None, require_nonempty=False):
    """Start-to-start cadence; never overlaps calls. Inject dependencies for tests."""
    run = run_once_with_retry if run is None else run
    interval = interval_from_env() if interval is None else interval_from_env(interval)
    stop = threading.Event() if stop is None else stop
    clock = time.monotonic if clock is None else clock
    wait = stop.wait if wait is None else wait
    emit = print if emit is None else emit
    if max_cycles is not None and (type(max_cycles) is not int or max_cycles < 0):
        raise ValueError('Invalid cycle count')
    if (audit_start is None) != (audit_finish is None):
        raise ValueError('Audit callbacks must be configured together')
    count = 0
    next_due = clock()
    while not stop.is_set() and (max_cycles is None or count < max_cycles):
        remaining = next_due - clock()
        if remaining > 0 and wait(remaining):
            break
        if stop.is_set():
            break
        started = clock()
        run_id = None
        outcome = None
        phase = 'audit_start'
        try:
            if audit_start is not None:
                run_id = audit_start()
                if not isinstance(run_id, str) or not run_id.strip():
                    raise ValueError('Audit start returned invalid run ID')
            phase = 'collection'
            outcome = run()
            outcome = safe_cycle_outcome(outcome, expected_symbols=expected_symbols, require_nonempty=require_nonempty)
            phase = 'audit_finish'
            if run_id is not None and audit_finish is not None:
                audit_finish(run_id, outcome['all_ok'])
                run_id = None
            emit(json.dumps({'event': 'trade_snapshot_cycle', 'cycle': count + 1,
                             'all_ok': outcome['all_ok'], 'results': outcome['results'],
                             'audit_persisted': run_id is None and audit_start is not None and audit_finish is not None,
                             'coverage_confirmed': False, 'is_cvd': False}, ensure_ascii=False))
        except Exception as exc:
            # A failed audit write must never be presented as a successful cycle.
            # If finish failed, do not retry it blindly: the commit may have succeeded.
            failure_audit_persisted = False
            if phase == 'collection' and run_id is not None and audit_finish is not None:
                try:
                    audit_finish(run_id, False)
                    failure_audit_persisted = True
                except Exception:
                    pass
            emit(json.dumps({'event': 'trade_snapshot_cycle', 'cycle': count + 1,
                             'all_ok': False, 'failure_phase': phase,
                             'error_type': type(exc).__name__,
                             'audit_persisted': failure_audit_persisted,
                             'coverage_confirmed': False, 'is_cvd': False}))
        count += 1
        # Skip missed ticks; do not run back-to-back to "catch up" after downtime.
        next_due = max(started + interval, clock())
    return count


def main():
    stop = threading.Event()
    def request_stop(_signum, _frame):
        stop.set()
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    from badang_trade_runs_461 import record_start, record_finish
    from badang_trade_job_455 import symbols_from_env
    return run_periodic(stop=stop, audit_start=record_start, audit_finish=record_finish,
                        expected_symbols=symbols_from_env(), require_nonempty=True)


if __name__ == '__main__':
    main()
