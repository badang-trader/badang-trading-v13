"""BADANG Trading 4.17: strict Bitget USDT-FUTURES candle adapter.
Only closed candles are used for calculations; last row is a disposable
in-progress/synthetic placeholder for legacy callers that use rows[:-1].
"""
import time
import re
import math
import requests

API='https://api.bitget.com'
FRAMES={'5m':('5m',300000),'15m':('15m',900000),'30m':('30m',1800000),
        '1H':('1H',3600000),'2H':('2H',7200000),'4H':('4H',14400000),
        '6H':('6H',21600000),'8H':('8H',28800000),'1D':('1Dutc',86400000)}
SESSION=requests.Session()

def _get(path, params):
    r=SESSION.get(API+path,params=params,timeout=12)
    r.raise_for_status()
    j=r.json()
    if str(j.get('code'))!='00000':
        raise ValueError('Bitget API error: '+str(j.get('msg','unknown'))[:100])
    return j.get('data') or []

def fastest_candles(symbol,timeframe,exchanges=None):
    if exchanges and any(str(x).lower()!='bitget' for x in exchanges):
        raise ValueError('Bitget-only mode: other exchanges disabled')
    if not re.fullmatch(r'[A-Z0-9]{2,25}USDT',symbol or ''):
        raise ValueError('Invalid Bitget USDT symbol')
    if timeframe not in FRAMES:
        raise ValueError('Unsupported timeframe: '+str(timeframe))
    gran, step=FRAMES[timeframe]
    start=time.monotonic()
    # Technical engine requires >=205 confirmed candles; fetch 350 when possible.
    # Some Bitget API versions cap a single page; paginate backwards if needed.
    try:
        raw=_get('/api/v2/mix/market/candles',
                 {'symbol':symbol,'productType':'USDT-FUTURES','granularity':gran,'limit':'350'})
    except (ValueError, requests.RequestException):
        raw=_get('/api/v2/mix/market/candles',
                 {'symbol':symbol,'productType':'USDT-FUTURES','granularity':gran,'limit':'200'})
    if not isinstance(raw,list):
        raise ValueError('Unexpected Bitget candle response format')
    # Obtain historical bars strictly before the oldest observed candle.
    # A failed history request is not silently treated as sufficient data.
    if len(raw)<210 and raw:
        oldest=min(int(r[0]) for r in raw if isinstance(r,(list,tuple)) and r)
        older=_get('/api/v2/mix/market/history-candles',
                   {'symbol':symbol,'productType':'USDT-FUTURES',
                    'granularity':gran,'endTime':str(oldest-1),'limit':'200'})
        if not isinstance(older,list):
            raise ValueError('Unexpected Bitget historical candle response')
        raw=older+raw
    now=int(time.time()*1000)
    rows=[]
    for r in raw:
        if not isinstance(r,(list,tuple)) or len(r)<6: continue
        try:
            t=int(r[0]); t=t*1000 if t<100000000000 else t
            o,h,l,c,v=map(float,r[1:6])
            if not (all(math.isfinite(z) for z in (o,h,l,c,v)) and min(o,h,l,c)>0
                    and h>=max(o,l,c) and l<=min(o,c) and v>=0): continue
            rows.append([str(t),str(o),str(h),str(l),str(c),str(v)])
        except (ValueError,TypeError,OverflowError): continue
    rows.sort(key=lambda x:int(x[0]))
    # Duplicate timestamps must not be silently reconciled.
    if len(set(r[0] for r in rows)) != len(rows):
        raise ValueError('Bitget duplicate candle timestamps')
    if len(rows)<206:
        raise ValueError('Insufficient Bitget candles for 205-bar analysis: '+str(len(rows)))
    # Do not fabricate missing historical bars. A placeholder is only used to
    # meet legacy callers' contract of excluding the last (unclosed) row.
    last_ts=int(rows[-1][0])
    if last_ts+step <= now:
        # The returned newest bar is already closed; append a disposable marker.
        marker=rows[-1].copy();marker[0]=str(last_ts+step)
        rows.append(marker)
    # If newest bar is forming, it will be excluded by legacy callers.
    return {'symbol':symbol,'timeframe':timeframe,'exchange':'bitget',
            'candles':rows,'latency_ms':round((time.monotonic()-start)*1000),
            'source':'Bitget USDT-FUTURES REST','observed_at_ms':now}

def bitget_derivatives_snapshot(symbol,candles):
    """Do not infer OI changes or complete CVD from isolated samples."""
    result={'source_exchange':'bitget','status':'RESEARCH_ONLY',
            'eligible_for_alert':False,'observed_at_ms':int(time.time()*1000),
            'oi_change_15m_pct':None,'oi_change_1h_pct':None,
            'oi_change_status':'UNAVAILABLE_NO_HISTORY',
            'trade_sample_count':0,'sample_imbalance':None,
            'sample_delta_contracts':None,'cvd_15m_contracts':None,
            'complete_hour_cvd':False,'funding_rate':None,'oi_contracts':None,
            'checks':{},'errors':{},
            'reason':'Bitget 전용: OI 변화와 전체 CVD는 동일 거래소 검증된 시계열 확보 전까지 미표시'}
    try:
        rows=_get('/api/v2/mix/market/open-interest',
                  {'symbol':symbol,'productType':'USDT-FUTURES'})
        if isinstance(rows,dict):
            oi=rows.get('openInterest') or rows.get('openInterestList')
            if isinstance(oi,list): oi=oi[0].get('size') if oi and isinstance(oi[0],dict) else None
            if oi is not None: result['oi_contracts']=float(oi)
    except Exception as exc: result['errors']['oi']=type(exc).__name__
    try:
        rows=_get('/api/v2/mix/market/current-fund-rate',
                  {'symbol':symbol,'productType':'USDT-FUTURES'})
        if isinstance(rows,list): rows=rows[0] if rows else {}
        if isinstance(rows,dict) and rows.get('fundingRate') is not None:
            result['funding_rate']=float(rows['fundingRate'])
    except Exception as exc: result['errors']['funding']=type(exc).__name__
    return result
