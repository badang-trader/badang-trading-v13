"""Read-only cross-check of worker lifecycle and per-symbol snapshot progress.

Neither successful runs nor recent samples prove complete market fills or CVD.
"""
import json
import time
from contextlib import closing
from badang_snapshot_progress_482 import check_progress
from badang_trade_runs_461 import assess_runs
from badang_trade_job_455 import symbols_from_env

SQL = ('SELECT started_ms,finished_ms,state FROM public.badang_trade_worker_runs '
       'ORDER BY started_ms DESC LIMIT 20')


def crosscheck(progress_fn=None, connect=None, now_ms=None, stale_after_ms=300000):
    result = {'status': 'CHECK_FAILED', 'worker_status': 'UNKNOWN',
              'snapshot_status': 'UNKNOWN', 'read_only': True,
              'coverage_confirmed': False, 'continuous_cvd_verified': False,
              'trading_ready': False, 'safe_to_enable_orders': False}
    try:
        now = int(time.time() * 1000) if now_ms is None else now_ms
        if type(now) is not int or now <= 0 or type(stale_after_ms) is not int or stale_after_ms <= 0:
            return result
        progress = (check_progress(now_ms=now) if progress_fn is None else progress_fn())
        if not isinstance(progress, dict):
            return result
        result['snapshot_status'] = progress.get('status', 'UNKNOWN') if isinstance(progress.get('status'), str) else 'UNKNOWN'
        # An explicitly non-read-only source cannot be accepted as a diagnostic.
        if 'read_only' in progress and progress['read_only'] is not True:
            result['status'] = 'UNSAFE_SNAPSHOT_SOURCE'
            return result
        # Never accept a downstream report that claims coverage, continuous CVD,
        # or order readiness from a recent REST-fill sample diagnostic.
        if any(k in progress and progress[k] is not False for k in ('coverage_confirmed',
                'continuous_cvd_verified', 'trading_ready', 'safe_to_enable_orders',
                'is_cvd', 'used_in_trading_score')):
            result['status'] = 'UNSUPPORTED_READINESS_CLAIM'
            return result
        # Do not query the database if preflight or snapshot assessment failed.
        if result['snapshot_status'] in ('PREFLIGHT_FAILED', 'QUERY_FAILED', 'UNKNOWN'):
            result['status'] = 'SNAPSHOT_CHECK_FAILED'
            return result
        if connect is None:
            from badang_oi_postgres_443 import _connection
            connect = _connection
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute(SQL)
                rows = cur.fetchall()
        worker = assess_runs(rows, now, stale_after_ms)
        result['worker_status'] = worker['status']
        result['historical_unfinished_count'] = worker.get('historical_unfinished_count', 0)
        # A successful worker run does not prove it produced the latest snapshots.
        # Require per-symbol timestamps and ensure they fall within the latest
        # completed run. A missing or malformed provenance record fails closed.
        latest_start = worker.get('latest_started_ms')
        latest_finish = worker.get('latest_finished_ms')
        samples = progress.get('symbols')
        aligned = (type(latest_start) is int and type(latest_finish) is int
                   and isinstance(samples, list) and len(samples) > 0)
        if aligned:
            expected = set(symbols_from_env())
            seen = set()
            for sample in samples:
                if not isinstance(sample, dict):
                    aligned = False
                    break
                if any(k in sample and sample[k] is not False for k in ('coverage_confirmed',
                        'continuous_cvd_verified', 'trading_ready', 'safe_to_enable_orders',
                        'is_cvd', 'used_in_trading_score')):
                    aligned = False
                    break
                name = sample.get('symbol')
                stamp = sample.get('latest_fetched_ms')
                if (not isinstance(name, str) or not name or name not in expected or name in seen
                    or sample.get('status') != 'TWO_RECENT_SAMPLES_ONLY'
                    or type(stamp) is not int
                    or not latest_start <= stamp <= latest_finish):
                    aligned = False
                    break
                seen.add(name)
            if seen != expected:
                aligned = False
        result['latest_run_snapshot_aligned'] = aligned
        result['status'] = ('RECENT_SAMPLES_AND_WORKER_ONLY'
                            if worker['status'] == 'RECENT_OK'
                            and result['snapshot_status'] == 'ALL_TWO_RECENT_SAMPLES_ONLY'
                            and aligned
                            and not worker.get('previous_run_unfinished', False)
                            else 'WORKER_OR_SNAPSHOT_WARNING')
    except Exception:
        result['status'] = 'CHECK_FAILED'
        result['worker_status'] = 'UNKNOWN'
    return result


def main():
    outcome = crosscheck()
    print(json.dumps(outcome, sort_keys=True, ensure_ascii=False))
    return 0 if outcome['status'] == 'RECENT_SAMPLES_AND_WORKER_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
