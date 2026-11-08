"""Bitget REST snapshots. Current forming candle is provisional; no fabricated CVD."""
import math, re, time, requests
from datetime import datetime, timezone
BASE='https://api.bitget.com'
FRAMES={'5m':300000,'15m':900000,'30m':1800000,'1H':3600000,'4H':14400000,'1D':86400000}
SESSION=requests.Session()

def number(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError,OverflowError): return None

def get(path,params):
    r=SESSION.get(BASE+path,params=params,timeout=8);r.raise_for_status();data=r.json()
    if str(data.get('code'))!='00000': raise ValueError('Bitget API: '+str(data.get('msg','error'))[:100])
    return data.get('data')

def normalize_candle(row,frame,now_ms):
    if not isinstance(row,(list,tuple)) or len(row)<6: raise ValueError('Invalid candle')
    ts=int(row[0]);ts=ts*1000 if ts<100000000000 else ts
    o,h,l,c,v=[number(z) for z in row[1:6]]
    if any(z is None for z in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c): raise ValueError('Invalid OHLCV')
    return {'start_ms':ts,'open':o,'high':h,'low':l,'close':c,'volume':v,'forming':ts+FRAMES[frame]>now_ms,'age_seconds':max(0,(now_ms-ts)//1000)}

def nearby(levels,price):
    # Only show levels on the correct side of current quote; no fabricated levels.
    supports=sorted({float(v) for v in levels if number(v) is not None and 0<float(v)<price},reverse=True)
    resistances=sorted({float(v) for v in levels if number(v) is not None and float(v)>price})
    return supports[:3],resistances[:3]

def snapshot(symbol,frames=('5m','15m','30m','1H')):
    if not re.fullmatch(r'[A-Z0-9]{2,25}USDT',symbol or ''): raise ValueError('Invalid symbol')
    now=int(time.time()*1000)
    ticker=get('/api/v2/mix/market/ticker',{'symbol':symbol,'productType':'USDT-FUTURES'})
    ticker=ticker[0] if isinstance(ticker,list) and ticker else ticker
    if not isinstance(ticker,dict): raise ValueError('Ticker unavailable')
    last=number(ticker.get('lastPr'));bid=number(ticker.get('bidPr'));ask=number(ticker.get('askPr'))
    if last is None or last<=0: raise ValueError('Ticker price unavailable')
    out={'symbol':symbol,'source':'Bitget USDT-FUTURES REST','fetched_at_ms':now,'last_price':last,
         'bid':bid,'ask':ask,'spread_pct':round((ask-bid)/last*100,5) if bid and ask and ask>=bid else None,
         'quote_is_live_stream':False,'candles':{},'errors':{},'flow':{'status':'NOT_VERIFIED','cvd':None,'oi_change':None,'reason':'체결 방향별 연속 수집 미연결: CVD·OI 변화 추정 금지'}}
    for tf in frames:
        if tf not in FRAMES:continue
        try:
            raw=get('/api/v2/mix/market/candles',{'symbol':symbol,'productType':'USDT-FUTURES','granularity':'1Dutc' if tf=='1D' else tf,'limit':'3'})
            if not isinstance(raw,list) or not raw:raise ValueError('No candles')
            parsed=sorted((normalize_candle(r,tf,now) for r in raw),key=lambda r:r['start_ms'])
            # Do not pretend that the newest returned candle is forming.
            out['candles'][tf]={'current':parsed[-1],'last_confirmed':next((r for r in reversed(parsed) if not r['forming']),None)}
        except Exception as exc:out['errors'][tf]=str(exc)[:120]
    try:
        oi=get('/api/v2/mix/market/open-interest',{'symbol':symbol,'productType':'USDT-FUTURES'})
        oi=oi[0] if isinstance(oi,list) and oi else oi
        if isinstance(oi,dict):
            out['flow']['oi_snapshot']=number(oi.get('size') or oi.get('openInterest'))
            out['flow']['oi_unit']='exchange reported (verify contract unit)'
    except Exception as exc:out['errors']['oi']=str(exc)[:120]
    try:
        funding=get('/api/v2/mix/market/current-fund-rate',{'symbol':symbol,'productType':'USDT-FUTURES'})
        funding=funding[0] if isinstance(funding,list) and funding else funding
        if isinstance(funding,dict):out['flow']['funding_rate']=number(funding.get('fundingRate'))
    except Exception as exc:out['errors']['funding']=str(exc)[:120]
    return out
