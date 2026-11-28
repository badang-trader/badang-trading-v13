"""Read-only two-snapshot progress diagnostic. Not a continuity or CVD proof."""
import json,time
from contextlib import closing
from badang_trade_job_455 import symbols_from_env
from badang_render_verify_479 import report

SQL = """SELECT symbol, fetched_ms FROM (
 SELECT symbol, fetched_ms, ROW_NUMBER() OVER
 (PARTITION BY symbol ORDER BY fetched_ms DESC) AS rn
 FROM public.badang_trade_snapshots WHERE symbol = ANY(%s)
) ranked WHERE rn <= 2 ORDER BY symbol, fetched_ms DESC"""

def check_progress(preflight_fn=None, connect=None, symbols=None, now_ms=None,
                   max_age_ms=300000, max_gap_ms=600000):
    result={'status':'PREFLIGHT_FAILED','read_only':True,'coverage_confirmed':False,
            'continuous_cvd_verified':False,'trading_ready':False,
            'safe_to_enable_orders':False,'symbols':[]}
    try:
        if type(max_age_ms) is not int or max_age_ms<=0 or type(max_gap_ms) is not int or max_gap_ms<=0:
            return result
        now=int(time.time()*1000) if now_ms is None else now_ms
        if type(now) is not int or now<=0: return result
        names=symbols_from_env() if symbols is None else symbols_from_env(','.join(symbols))
        gate=report(True) if preflight_fn is None else preflight_fn()
        if not isinstance(gate,dict) or gate.get('status')!='DATABASE_PREFLIGHT_PASSED': return result
        result['status']='QUERY_FAILED'
        if connect is None:
            from badang_oi_postgres_443 import _connection
            connect=_connection
        with closing(connect()) as con:
            with con.cursor() as cur:
                cur.execute(SQL,(names,))
                rows=cur.fetchall()
        if not isinstance(rows,(tuple,list)): return result
        stamps={name:[] for name in names}
        for row in rows:
            if not isinstance(row,(tuple,list)) or len(row)!=2: return result
            name,stamp=row
            if name not in stamps or type(stamp) is not int or stamp<=0 or stamp>now: return result
            existing=stamps[name]
            if len(existing)>=2 or (existing and stamp>=existing[-1]): return result
            existing.append(stamp)
        for name in names:
            history=stamps[name]
            latest=history[0] if history else None
            gap=history[0]-history[1] if len(history)==2 else None
            age=now-latest if latest is not None else None
            if age is None: state='NO_SAMPLES'
            elif age>max_age_ms: state='STALE_SAMPLE'
            elif gap is None: state='INSUFFICIENT_HISTORY'
            elif gap>max_gap_ms: state='LARGE_SNAPSHOT_GAP'
            else: state='TWO_RECENT_SAMPLES_ONLY'
            result['symbols'].append({'symbol':name,'status':state,'latest_fetched_ms':latest,
                'previous_fetched_ms':history[1] if len(history)==2 else None,
                'snapshot_age_ms':age,'snapshot_gap_ms':gap,'coverage_confirmed':False,'is_cvd':False})
        result['status']=('ALL_TWO_RECENT_SAMPLES_ONLY' if all(x['status']=='TWO_RECENT_SAMPLES_ONLY' for x in result['symbols']) else 'PROGRESS_INCOMPLETE')
    except Exception:
        result['status']='QUERY_FAILED' if result['status']!='PREFLIGHT_FAILED' else 'PREFLIGHT_FAILED'
        result['symbols']=[]
    return result

def main():
    result=check_progress()
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0 if result['status']=='ALL_TWO_RECENT_SAMPLES_ONLY' else 1

if __name__=='__main__': raise SystemExit(main())
