"""BADANG Trading 1.3 — standalone rule-based futures technical analysis.

No network calls. Supply confirmed exchange OHLCV and optional OI/funding data.
Signals are heuristic, not forecasts or investment advice.
"""
from __future__ import annotations

from statistics import mean
from typing import Any
import math


def _num(v: Any) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else float('nan')
    except (TypeError, ValueError):
        return float('nan')


def normalize(candles: list) -> list[dict]:
    """Accept [timestamp,open,high,low,close,volume] or OHLCV dictionaries."""
    out = []
    for c in candles:
        if isinstance(c, dict):
            d = {k: _num(c.get(k)) for k in ('open','high','low','close','volume')}
        else:
            if len(c) < 6:
                continue
            d = dict(zip(('open','high','low','close','volume'), map(_num, c[1:6])))
        if not all(math.isfinite(v) for v in d.values()):
            continue
        if d['low'] <= 0 or d['high'] < max(d['open'],d['close'],d['low']) or d['low'] > min(d['open'],d['close']) or d['volume'] < 0:
            continue
        out.append(d)
    return out


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2/(period+1)
    result = [values[0]]
    for x in values[1:]:
        result.append(x*k + result[-1]*(1-k))
    return result


def rsi(values: list[float], period: int=14) -> list[float | None]:
    result = [None]*len(values)
    if len(values) <= period:
        return result
    changes = [values[i]-values[i-1] for i in range(1,len(values))]
    gains = sum(max(v,0) for v in changes[:period])/period
    losses = sum(max(-v,0) for v in changes[:period])/period
    def calc(g,l):
        return 100 if l == 0 and g > 0 else 50 if l == 0 else 100 - 100/(1+g/l)
    result[period] = calc(gains,losses)
    for i in range(period+1,len(values)):
        change = changes[i-1]
        gains = (gains*(period-1)+max(change,0))/period
        losses = (losses*(period-1)+max(-change,0))/period
        result[i] = calc(gains,losses)
    return result


def atr(rows: list[dict], period: int=14) -> float:
    tr = []
    for i in range(1,len(rows)):
        r, prev = rows[i], rows[i-1]
        tr.append(max(r['high']-r['low'], abs(r['high']-prev['close']), abs(r['low']-prev['close'])))
    return mean(tr[-period:]) if len(tr)>=period else 0.0


def pivots(rows: list[dict], radius: int=3) -> list[tuple[int,str,float]]:
    points = []
    for i in range(radius,len(rows)-radius):
        segment = rows[i-radius:i+radius+1]
        if rows[i]['high'] == max(r['high'] for r in segment):
            points.append((i,'H',rows[i]['high']))
        if rows[i]['low'] == min(r['low'] for r in segment):
            points.append((i,'L',rows[i]['low']))
    # Collapse consecutive same-type pivots to the more extreme one.
    result = []
    for p in points:
        if result and result[-1][1] == p[1]:
            if (p[1]=='H' and p[2]>result[-1][2]) or (p[1]=='L' and p[2]<result[-1][2]):
                result[-1] = p
        else:
            result.append(p)
    return result


def divergence(points, rsi_series):
    signals = []
    for typ, label in [('L','bullish'),('H','bearish')]:
        relevant = [p for p in points if p[1]==typ and rsi_series[p[0]] is not None]
        if len(relevant)<2:
            continue
        a,b = relevant[-2:]
        ra,rb = rsi_series[a[0]],rsi_series[b[0]]
        if typ=='L' and b[2]<a[2] and rb>ra+2:
            signals.append(label)
        if typ=='H' and b[2]>a[2] and rb<ra-2:
            signals.append(label)
    return signals


def wave_candidates(points):
    """Tentative geometric patterns, not definitive Elliott labeling."""
    recent = points[-9:]
    patterns = []
    # Three alternating swings can suggest an ABC correction, but not prove it.
    if len(recent)>=4:
        p = recent[-4:]
        moves = [p[i+1][2]-p[i][2] for i in range(3)]
        if moves[0]*moves[1]<0 and moves[1]*moves[2]<0:
            patterns.append({'pattern':'ABC candidate','confidence':'low','direction':'up' if moves[-1]>0 else 'down'})
    if len(recent)>=6:
        p = recent[-6:]
        moves = [p[i+1][2]-p[i][2] for i in range(5)]
        direction = 1 if moves[0]>0 else -1
        if all(moves[i]*direction > 0 for i in (0,2,4)) and all(moves[i]*direction < 0 for i in (1,3)):
            patterns.append({'pattern':'5-swing impulse candidate','confidence':'low','direction':'up' if direction>0 else 'down'})
    if len(recent)>=7:
        patterns.append({'pattern':'WXY possible; not confirmed','confidence':'unverified','direction':'unknown'})
    return patterns


def analyze(candles: list, mode: str='scalp', funding_rate=None, oi_change_pct=None, symbol: str='') -> dict:
    rows = normalize(candles)
    if len(rows)<205:
        return {'symbol':symbol,'status':'insufficient_data','count':len(rows),'recommendation':'WAIT'}
    close = [r['close'] for r in rows]
    e20,e50,e200 = (ema(close,n)[-1] for n in (20,50,200))
    rs = rsi(close)
    macd = [a-b for a,b in zip(ema(close,12),ema(close,26))]
    signal = ema(macd,9)
    hist = macd[-1]-signal[-1]
    prev_hist = macd[-2]-signal[-2]
    p = close[-1]
    points = pivots(rows)
    div = divergence(points,rs)
    vol_avg = mean(r['volume'] for r in rows[-21:-1])
    vol_ratio = rows[-1]['volume']/vol_avg if vol_avg>0 else 0
    volatility = atr(rows)
    highs = [x[2] for x in points if x[1]=='H']
    lows = [x[2] for x in points if x[1]=='L']
    # The most recent confirmed swing anchors define an indicative Fibonacci zone.
    recent_hi = max(r['high'] for r in rows[-60:])
    recent_lo = min(r['low'] for r in rows[-60:])
    span = recent_hi-recent_lo
    fib = {'retracement_382':recent_hi-0.382*span,
           'retracement_500':recent_hi-0.5*span,
           'retracement_618':recent_hi-0.618*span,
           'extension_1272_up':recent_hi+0.272*span,
           'extension_1272_down':recent_lo-0.272*span}
    long_score=short_score=50
    reasons_long=[]; reasons_short=[]
    def score(side, points, reason):
        nonlocal long_score,short_score
        if side=='long':
            long_score+=points; reasons_long.append(reason)
        else:
            short_score+=points; reasons_short.append(reason)
    if p>e20>e50>e200: score('long',18,'EMA bullish alignment')
    if p<e20<e50<e200: score('short',18,'EMA bearish alignment')
    if e20>e50: score('long',8,'EMA20 above EMA50')
    elif e20<e50: score('short',8,'EMA20 below EMA50')
    if hist>0 and hist>prev_hist: score('long',12,'MACD histogram rising positive')
    if hist<0 and hist<prev_hist: score('short',12,'MACD histogram falling negative')
    if rs[-1] is not None:
        if 50<rs[-1]<72: score('long',8,'RSI bullish range')
        if 28<rs[-1]<50: score('short',8,'RSI bearish range')
    if 'bullish' in div: score('long',12,'bullish RSI divergence candidate')
    if 'bearish' in div: score('short',12,'bearish RSI divergence candidate')
    if vol_ratio>=1.5:
        if close[-1]>close[-2]: score('long',8,'rising volume with green candle')
        elif close[-1]<close[-2]: score('short',8,'rising volume with red candle')
    # Optional futures inputs: missing data is NOT treated as zero.
    f = _num(funding_rate) if funding_rate is not None else None
    oi = _num(oi_change_pct) if oi_change_pct is not None else None
    if f is not None and math.isfinite(f):
        if f>0.0005: score('short',4,'high positive funding: crowded longs')
        elif f< -0.0005: score('long',4,'negative funding: crowded shorts')
    if oi is not None and math.isfinite(oi) and oi>3:
        if close[-1]>close[-2]: score('long',5,'OI rising with price')
        elif close[-1]<close[-2]: score('short',5,'OI rising while price falls')
    long_score=min(100,long_score);short_score=min(100,short_score)
    side='LONG' if long_score>short_score else 'SHORT'
    best=max(long_score,short_score)
    direction=1 if side=='LONG' else -1
    # Stop beyond recent confirmed swing or 1.5 ATR, whichever is farther.
    recent_low = min(lows[-3:]) if lows else min(r['low'] for r in rows[-20:])
    recent_high = max(highs[-3:]) if highs else max(r['high'] for r in rows[-20:])
    stop = min(recent_low,p-1.5*volatility) if direction==1 else max(recent_high,p+1.5*volatility)
    risk=abs(p-stop)
    target1=p+direction*1.5*risk
    target2=p+direction*2.0*risk
    rr=abs(target1-p)/risk if risk>0 else 0
    # Price-at-market is a reference, not an executable quote.
    recommended = best>=80 and rr>=1.5 and volatility>0 and len(reasons_long if side=='LONG' else reasons_short)>=3
    return {
        'symbol':symbol,'status':'ok','mode':mode,'recommendation':side if recommended else 'WAIT',
        'candidate_side':side,'long_score':long_score,'short_score':short_score,
        'entry_reference':p,'stop_loss':stop,'take_profit_1':target1,'take_profit_2':target2,
        'risk_reward_1':round(rr,2),'rsi':round(rs[-1],2),'macd_histogram':hist,
        'ema20':e20,'ema50':e50,'ema200':e200,'volume_ratio':round(vol_ratio,2),
        'atr14':volatility,'divergences':div,'wave_candidates':wave_candidates(points),
        'fibonacci':fib,'funding_rate':f,'oi_change_pct':oi,
        'futures_data_available':{'funding':f is not None and math.isfinite(f),'oi':oi is not None and math.isfinite(oi)},
        'reasons':reasons_long if side=='LONG' else reasons_short,
        'caveats':['Single-timeframe only: confirm higher timeframe before acting',
                   'Wave labels are unconfirmed geometric candidates',
                   'Price targets exclude fees, slippage, and funding costs']
    }


def top_five(analyses: list[dict]) -> list[dict]:
    eligible = [a for a in analyses if a.get('recommendation') in ('LONG','SHORT') and a.get('status')=='ok']
    return sorted(eligible,key=lambda a:max(a['long_score'],a['short_score']),reverse=True)[:5]
