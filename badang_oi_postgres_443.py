"""Durable Bitget OI observations. Requires DATABASE_URL and external scheduler.
No scheduler runs inside the web workers.
"""
import os
import math
import time
from contextlib import closing
from badang_oi_history_441 import _valid_symbol

SCHEMA = '''CREATE TABLE IF NOT EXISTS badang_oi_observations (
 symbol TEXT NOT NULL, exchange TEXT NOT NULL, observed_ms BIGINT NOT NULL,
 oi DOUBLE PRECISION NOT NULL CHECK (oi > 0),
 PRIMARY KEY(symbol, exchange, observed_ms))'''

def _connection():
    import psycopg2
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        raise RuntimeError('DATABASE_URL required for durable OI storage')
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return psycopg2.connect(url, connect_timeout=5)

def retention_days():
    # Preserve longer swing history while bounding database growth.
    try:
        return max(30,min(365,int(os.environ.get('BADANG_OI_RETENTION_DAYS','90'))))
    except (ValueError,TypeError):
        return 90

def record(symbol, oi, observed_ms=None):
    symbol = _valid_symbol(symbol)
    oi = float(oi)
    import math
    if not math.isfinite(oi) or oi <= 0:
        raise ValueError('Invalid OI')
    now = int(time.time() * 1000)
    observed_ms = now if observed_ms is None else int(observed_ms)
    if not now - 86_400_000 <= observed_ms <= now + 60_000:
        raise ValueError('Invalid observation time')
    with closing(_connection()) as con:
        with con:
            with con.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute('INSERT INTO badang_oi_observations VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                            (symbol, 'bitget', observed_ms, oi))
                cur.execute('DELETE FROM badang_oi_observations WHERE observed_ms < %s', (now-retention_days()*86_400_000,))
    return {'symbol':symbol,'oi':oi,'observed_ms':observed_ms}

def changes(symbol, now_ms=None, tolerance_ms=90_000, freshness_ms=180_000):
    symbol = _valid_symbol(symbol)
    now_ms = int(time.time()*1000) if now_ms is None else int(now_ms)
    result = {'source_exchange':'bitget','symbol':symbol,'status':'INSUFFICIENT_HISTORY',
              'collection':'EXTERNAL_SCHEDULE_REQUIRED','storage_durable':True,
              'retention_days':retention_days(),
              'oi_change_15m_pct':None,'oi_change_1h_pct':None,
              'reason':'동일 거래소의 과거 관측값 필요'}
    with closing(_connection()) as con:
        with con.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute('SELECT observed_ms, oi FROM badang_oi_observations WHERE symbol=%s AND exchange=%s AND observed_ms<=%s ORDER BY observed_ms DESC LIMIT 2000',
                        (symbol,'bitget',now_ms))
            rows = cur.fetchall()
    if not rows or rows[0][0] > now_ms or now_ms - rows[0][0] > freshness_ms:
        result['status']='STALE_OR_MISSING_CURRENT'
        return result
    latest_t, latest_oi = rows[0]
    if latest_oi is None or not math.isfinite(float(latest_oi)) or float(latest_oi) <= 0:
        result['status'] = 'INVALID_CURRENT_OI'
        return result
    result.update(current_oi=latest_oi,current_observed_ms=latest_t)
    for label, period in [('15m',900_000),('1h',3_600_000)]:
        target = latest_t-period
        matches = [(abs(t-target),t,oi) for t,oi in rows[1:]
                   if 0 <= target-t <= tolerance_ms and oi is not None
                   and math.isfinite(float(oi)) and float(oi)>0]
        if matches:
            _, baseline_t, baseline_oi = min(matches)
            result['oi_change_'+label+'_pct']=round((latest_oi/baseline_oi-1)*100,5)
            result[label+'_baseline_ms']=baseline_t
    available = sum(result['oi_change_'+k+'_pct'] is not None for k in ('15m','1h'))
    result['status']='HISTORY_AVAILABLE' if available==2 else 'PARTIAL_HISTORY' if available else 'INSUFFICIENT_HISTORY'
    return result

def observe(symbol):
    from badang_oi_history_441 import _valid_symbol
    from bitget_market_data import _get
    symbol=_valid_symbol(symbol)
    rows=_get('/api/v2/mix/market/open-interest',{'symbol':symbol,'productType':'USDT-FUTURES'})
    from badang_oi_parser_446 import parse_open_interest
    oi = parse_open_interest(rows)
    record(symbol,oi)
    return changes(symbol)


def wave_interval_change(symbol, start_ms, end_ms, tolerance_ms=90000):
    """Read-only endpoint OI comparison; no observation after either boundary."""
    symbol=_valid_symbol(symbol)
    if not (0<=start_ms<end_ms<=int(time.time()*1000)) or not 0<tolerance_ms<=180000:
        raise ValueError('Invalid wave interval')
    result={'source_exchange':'bitget','status':'INSUFFICIENT_HISTORY',
            'start_ms':start_ms,'end_ms':end_ms,'oi_change_pct':None,
            'cvd':None,'used_in_score':False}
    with closing(_connection()) as con:
        with con.cursor() as cur:
            points=[]
            for boundary in (start_ms,end_ms):
                cur.execute('SELECT observed_ms, oi FROM badang_oi_observations WHERE symbol=%s AND exchange=%s AND observed_ms BETWEEN %s AND %s ORDER BY observed_ms DESC LIMIT 1',
                            (symbol,'bitget',boundary-tolerance_ms,boundary))
                points.append(cur.fetchone())
    if any(p is None or not math.isfinite(float(p[1])) or p[1]<=0 for p in points):
        return result
    first,last=points
    if last[0]<=first[0]:
        return result
    result.update(status='ENDPOINTS_AVAILABLE',start_observed_ms=first[0],
                  end_observed_ms=last[0],oi_change_pct=round((last[1]/first[1]-1)*100,5),
                  continuous_coverage_verified=False)
    return result
