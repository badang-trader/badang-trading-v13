"""Historical closed-candle integrity gate for independent BADANG research.

Input must be an exchange export containing UTC millisecond timestamps and
OHLCV, ordered oldest first. This module does not fetch or invent market data.
"""
import math

FRAME_MS={'15m':900000,'30m':1800000,'1H':3600000,'4H':14400000,'1D':86400000}

def audit_historical_candles(rows,timeframe,*,asof_ms=None):
    if timeframe not in FRAME_MS: raise ValueError('unsupported timeframe')
    step=FRAME_MS[timeframe]
    if asof_ms is None: raise ValueError('asof_ms required to prove closed bars')
    if not isinstance(asof_ms,int) or isinstance(asof_ms,bool) or asof_ms<=0:
        raise ValueError('invalid asof timestamp')
    if not rows: raise ValueError('empty history')
    prev=None
    start=None
    for i,row in enumerate(rows):
        if len(row)<6: raise ValueError('missing OHLCV fields')
        ts=row[0]
        if not isinstance(ts,int) or isinstance(ts,bool) or ts<0 or ts%step:
            raise ValueError('invalid or misaligned UTC timestamp at '+str(i))
        try: o,h,l,c,v=(float(x) for x in row[1:6])
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('non-numeric OHLCV') from exc
        if not all(math.isfinite(x) for x in (o,h,l,c,v)) or l<=0 or v<0 or l>min(o,c) or h<max(o,c):
            raise ValueError('invalid OHLCV range at '+str(i))
        if ts+step>asof_ms: raise ValueError('forming or future candle included')
        if prev is not None and ts-prev!=step:
            raise ValueError('missing, duplicate or unsorted candles at '+str(i))
        if start is None: start=ts
        prev=ts
    return {'status':'VALID_CLOSED_CONTIGUOUS','timeframe':timeframe,
            'bars':len(rows),'start_ms':start,'last_open_ms':prev,
            'last_close_ms':prev+step,'asof_ms':asof_ms,
            'source':'CALLER_SUPPLIED_NOT_VERIFIED'}
