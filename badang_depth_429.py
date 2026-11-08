"""Conservative multi-timeframe Bitget candle depth / structure review.
No trade authorization, no synthetic CVD, no unconfirmed Elliott wave labels.
"""
import math
import time
from badang_live_428 import get, normalize_candle, FRAMES, number
from badang_wave_433 import wave_candidates
from badang_wave_434 import audit_candidates

TIMEFRAMES = ('5m','15m','30m','1H','4H')


def validate_bars(rows, frame, now_ms):
    parsed = sorted((normalize_candle(r, frame, now_ms) for r in rows), key=lambda b:b['start_ms'])
    unique = {b['start_ms']:b for b in parsed}
    bars = [unique[k] for k in sorted(unique)]
    gaps = [(bars[i-1]['start_ms'],bars[i]['start_ms']) for i in range(1,len(bars))
            if bars[i]['start_ms']-bars[i-1]['start_ms'] != FRAMES[frame]]
    closed = [b for b in bars if not b['forming'] and b['start_ms']+FRAMES[frame]<=now_ms]
    lag = (now_ms-(closed[-1]['start_ms']+FRAMES[frame]))/1000 if closed else None
    return bars,closed,{'count':len(bars),'closed_count':len(closed),'gaps':len(gaps),
                        'last_closed_age_seconds':round(lag,1) if lag is not None else None,
                        'usable':len(closed)>=60 and not gaps and lag is not None and lag<=FRAMES[frame]/1000*2}


def pivots(bars, window=3):
    pts=[]
    for i in range(window,len(bars)-window):
        segment=bars[i-window:i+window+1]
        if bars[i]['high'] == max(b['high'] for b in segment):
            pts.append(('R',bars[i]['high'],bars[i]['start_ms'],i))
        if bars[i]['low'] == min(b['low'] for b in segment):
            pts.append(('S',bars[i]['low'],bars[i]['start_ms'],i))
    return pts


def levels(bars, current_price, atr):
    if len(bars)<25 or not atr or atr<=0:return {'supports':[],'resistances':[],'method':'INSUFFICIENT_DATA'}
    pts=pivots(bars[-160:])
    # Cluster price levels within a volatility-aware tolerance. Do not call this a proven support/resistance.
    tolerance=max(atr*.35,current_price*.0005)
    clusters=[]
    for kind,px,ts,idx in pts:
        match=next((z for z in clusters if z['kind']==kind and abs(z['price']-px)<=tolerance),None)
        if match:
            n=match['touches'];match['price']=(match['price']*n+px)/(n+1)
            match['touches']+=1;match['last_touch_ms']=max(match['last_touch_ms'],ts)
        else:clusters.append({'kind':kind,'price':px,'touches':1,'last_touch_ms':ts})
    def rank(z):return (-z['touches'],abs(z['price']-current_price),-z['last_touch_ms'])
    supports=sorted((z for z in clusters if z['kind']=='S' and z['price']<current_price),key=rank)[:5]
    resistances=sorted((z for z in clusters if z['kind']=='R' and z['price']>current_price),key=rank)[:5]
    return {'supports':supports,'resistances':resistances,'method':'CONFIRMED_SWING_CLUSTER',
            'tolerance':round(tolerance,8),'note':'확정봉 스윙 전환점 군집; 터치 횟수는 지지·저항 성공률이 아님'}


def ema(values,period):
    if len(values)<period:return None
    avg=sum(values[:period])/period;k=2/(period+1)
    for x in values[period:]:avg=k*x+(1-k)*avg
    return avg


def atr14(bars):
    if len(bars)<15:return None
    tr=[]
    for i in range(1,len(bars)):
        b,p=bars[i],bars[i-1]
        tr.append(max(b['high']-b['low'],abs(b['high']-p['close']),abs(b['low']-p['close'])))
    return sum(tr[-14:])/14


def fetch_candles(symbol,frame,limit=320):
    """Page backward by candle start timestamp; do not treat missing history as zero."""
    if frame not in FRAMES:raise ValueError('Unsupported timeframe')
    result={}
    end=None
    for _ in range(4):
        params={'symbol':symbol,'productType':'USDT-FUTURES',
                'granularity':'1Dutc' if frame=='1D' else frame,
                'limit':str(min(200, max(1,limit-len(result))))}
        if end is not None:params['endTime']=str(end)
        raw=get('/api/v2/mix/market/candles',params)
        if not isinstance(raw,list) or not raw:break
        timestamps=[]
        for row in raw:
            ts=int(row[0]);ts=ts*1000 if ts<100000000000 else ts
            timestamps.append(ts)
            result[ts]=row
        if len(result)>=limit:break
        older=min(timestamps)-1
        if end is not None and older>=end:break
        end=older
    return [result[t] for t in sorted(result)][-limit:]


def analyze_depth(symbol,frames=('15m','30m','1H','4H')):
    import re
    if not re.fullmatch(r'[A-Z0-9]{2,25}USDT',symbol or ''):raise ValueError('Invalid symbol')
    now=int(time.time()*1000)
    output={'symbol':symbol,'source':'Bitget USDT futures candles','fetched_at_ms':now,
            'timeframes':{},'errors':{},'requested_bars':320,'warning':'확정봉 지지·저항 참고값. 현재 진행봉과 실제 체결 수급은 별도이며 승률 아님.'}
    for tf in frames:
        try:
            raw=fetch_candles(symbol,tf)
            bars,closed,quality=validate_bars(raw,tf,now)
            if not closed:raise ValueError('No confirmed candles')
            closes=[b['close'] for b in closed]
            current=bars[-1]
            volatility=atr14(closed)
            structure=levels(closed,current['close'],volatility)
            output['timeframes'][tf]={'quality':quality,'forming':current if current['forming'] else None,
                'last_closed':closed[-1], 'ema20':ema(closes,20),'ema50':ema(closes,50),
                'ema200':ema(closes,200),'atr14':volatility,'levels':structure,
                'analysis_status':'VALID' if quality['usable'] and len(closed)>=200 else 'LIMITED',
                'ema200_ready':len(closed)>=200,
                'current_price':current['close'],
                'nearest_support':max((z['price'] for z in structure['supports']),default=None),
                'nearest_resistance':min((z['price'] for z in structure['resistances']),default=None),
                'wave_status':'HEURISTIC_CANDIDATES_ONLY', 'wave_candidates_433':wave_candidates(closed,volatility),
                'wave_audit_434':audit_candidates(wave_candidates(closed,volatility),closed,volatility)}
        except Exception as exc:output['errors'][tf]=str(exc)[:140]
    return output
