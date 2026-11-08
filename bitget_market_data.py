"""BADANG Trading 4.17: strict Bitget USDT-FUTURES candle adapter.
Only closed candles are used for calculations; last row is a disposable
in-progress/synthetic placeholder for legacy callers that use rows[:-1].
"""
import time
import re
import math
import requests
import threading

API='https://api.bitget.com'
FRAMES={'5m':('5m',300000),'15m':('15m',900000),'30m':('30m',1800000),
        '1H':('1H',3600000),'2H':('2H',7200000),'4H':('4H',14400000),
        '6H':('6H',21600000),'8H':('8H',28800000),'1D':('1Dutc',86400000)}
SESSION=requests.Session()

_REQUEST_LOCK=threading.Lock()
_LAST_REQUEST=[0.0]

def _get(path, params):
    """Bounded retries for rate limits; never substitute stale candles."""
    for attempt in range(3):
        with _REQUEST_LOCK:
            wait=max(0.0, 0.16-(time.monotonic()-_LAST_REQUEST[0]))
            if wait: time.sleep(wait)
            _LAST_REQUEST[0]=time.monotonic()
            r=SESSION.get(API+path,params=params,timeout=12)
        if r.status_code==429:
            if attempt==2:
                raise ValueError('Bitget 요청 제한(HTTP 429): 재시도 3회 실패')
            retry_after=r.headers.get('Retry-After','')
            try: delay=max(0.5,min(float(retry_after),4.0))
            except (ValueError,TypeError): delay=0.8*(attempt+1)
            time.sleep(delay)
            continue
        r.raise_for_status()
        j=r.json()
        if str(j.get('code'))=='00000':
            return j.get('data') or []
        if str(j.get('code')) in ('429','40015','40017'):
            if attempt==2:
                raise ValueError('Bitget API 요청 제한: 재시도 3회 실패')
            time.sleep(0.8*(attempt+1))
            continue
        raise ValueError('Bitget API error: '+str(j.get('msg','unknown'))[:100])
    raise ValueError('Bitget API 재시도 실패')

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
    except ValueError as exc:
        # Only retry with a smaller page if the exchange explicitly rejects
        # the page size. Rate limits, transport errors and malformed responses
        # must not trigger an additional request burst.
        message=str(exc).lower()
        if not (('limit' in message or 'page size' in message) and
                ('invalid' in message or 'exceed' in message or
                 'maximum' in message or 'range' in message)):
            raise
        raw=_get('/api/v2/mix/market/candles',
                 {'symbol':symbol,'productType':'USDT-FUTURES','granularity':gran,'limit':'200'})
    if not isinstance(raw,list):
        raise ValueError('Unexpected Bitget candle response format')
    # Bitget can return fewer bars than requested, particularly for 4H/1D.
    # Keep paging backward until the engine has enough confirmed bars.
    # An empty page, repeated cursor or API error is reported, never filled.
    seen={}
    def ingest(page):
        for item in page:
            if not isinstance(item,(list,tuple)) or not item: continue
            try:
                stamp=int(item[0]); stamp=stamp*1000 if stamp<100000000000 else stamp
            except (TypeError,ValueError): continue
            if stamp in seen and list(seen[stamp])!=list(item):
                raise ValueError('Conflicting Bitget candle timestamp: '+str(stamp))
            seen[stamp]=item
    ingest(raw)
    cursor=None
    for _ in range(12):
        now_ms=int(time.time()*1000)
        closed=sum(1 for t in seen if t+step<=now_ms)
        if closed>=220: break
        if not seen: break
        oldest=min(seen)
        next_cursor=oldest-step
        if cursor is not None and next_cursor>=cursor:
            raise ValueError('Bitget history pagination did not advance')
        cursor=next_cursor
        page=_get('/api/v2/mix/market/history-candles',
                  {'symbol':symbol,'productType':'USDT-FUTURES',
                   'granularity':gran,'endTime':str(cursor),'limit':'200'})
        if not isinstance(page,list):
            raise ValueError('Unexpected Bitget historical candle response')
        if not page: break
        before=len(seen)
        ingest(page)
        if len(seen)==before: break
    # Detect missing bars in the most recent 260 slots. Re-query the exact
    # surrounding window; only accept real exchange candles (never interpolate).
    # Include a buffer because the final row may still be forming.
    for _repair_round in range(2):
        stamps=sorted(seen)
        if len(stamps)<2: break
        gaps=[(left,right) for left,right in zip(stamps[-262:-1],stamps[-261:])
              if right-left>step and (right-left)%step==0]
        if not gaps: break
        added=0
        for left,right in gaps[:12]:
            try:
                patch=_get('/api/v2/mix/market/history-candles',
                    {'symbol':symbol,'productType':'USDT-FUTURES',
                     'granularity':gran,'startTime':str(max(0,left-step)),
                     'endTime':str(right+step),'limit':'200'})
            except (ValueError,requests.RequestException):
                continue
            before=len(seen)
            if isinstance(patch,list): ingest(patch)
            added+=len(seen)-before
        if added==0: break
    raw=list(seen.values())
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
    # The scoring engine requires 205 *consecutive* completed candles.
    # Restrict to the latest contiguous block, so historical holes never
    # contaminate EMA200, RSI, MACD, or wave analysis.
    complete=[r for r in rows if int(r[0])+step<=now]
    if complete:
        contiguous=[complete[-1]]
        for r in reversed(complete[:-1]):
            if int(contiguous[-1][0])-int(r[0]) != step: break
            contiguous.append(r)
        if len(contiguous)<205:
            raise ValueError('Bitget 연속 확정봉 부족: '+str(len(contiguous))+
                             '개 / 최소 205개 (과거 누락 또는 페이지 조회 문제)')
        # Keep only the contiguous history and an existing unfinished candle.
        rows=list(reversed(contiguous)) + [r for r in rows if int(r[0])>int(complete[-1][0])]
    else:
        raise ValueError('Bitget 확정봉 자료 없음')
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
