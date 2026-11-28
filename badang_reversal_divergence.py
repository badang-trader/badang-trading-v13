"""Causal RSI/MACD pivot divergence research; no order access.

Indicators and pivots are computed from closed OHLCV. Each divergence becomes
available only when the second price pivot is confirmed by right-side candles.
"""
from badang_real_pivot_audit import confirmed_pivots

def _ema(values,n):
    alpha=2/(n+1)
    out=[]
    for x in values:
        out.append(x if not out else alpha*x+(1-alpha)*out[-1])
    return out

def _rsi(values,n=14):
    gains=[];losses=[]
    for i in range(1,len(values)):
        change=values[i]-values[i-1]
        gains.append(max(change,0));losses.append(max(-change,0))
    result=[None]*len(values)
    if len(gains)<n:return result
    ag=sum(gains[:n])/n;al=sum(losses[:n])/n
    result[n]=100 if al==0 else 100-100/(1+ag/al)
    for i in range(n+1,len(values)):
        ag=(ag*(n-1)+gains[i-1])/n
        al=(al*(n-1)+losses[i-1])/n
        result[i]=100 if al==0 else 100-100/(1+ag/al)
    return result

def confirmed_divergences(rows,left=3,right=3):
    if len(rows)<35:return []
    closes=[float(r[4]) for r in rows]
    fast=_ema(closes,12);slow=_ema(closes,26)
    macd=[a-b for a,b in zip(fast,slow)]
    rsi=_rsi(closes)
    pivots=confirmed_pivots(rows,left=left,right=right)
    result=[]
    for kind in ('LOW','HIGH'):
        same=[p for p in pivots if p['type']==kind]
        for p,q in zip(same,same[1:]):
            i=p['pivot_bar'];j=q['pivot_bar']
            if j<=i or j+right>=len(rows):continue
            for indicator,values in (('RSI',rsi),('MACD',macd)):
                a,b=values[i],values[j]
                if a is None or b is None:continue
                classification=None
                if kind=='LOW':
                    if q['price']<p['price'] and b>a:classification='REGULAR_BULLISH'
                    elif q['price']>p['price'] and b<a:classification='HIDDEN_BULLISH'
                else:
                    if q['price']>p['price'] and b<a:classification='REGULAR_BEARISH'
                    elif q['price']<p['price'] and b>a:classification='HIDDEN_BEARISH'
                if classification:
                    result.append({'indicator':indicator,'classification':classification,
                        'first_pivot_bar':i,'second_pivot_bar':j,
                        'available_at_bar':q['confirmed_at_bar'],
                        'available_at_timestamp_ms':rows[q['confirmed_at_bar']][0],
                        'first_price':p['price'],'second_price':q['price'],
                        'first_indicator':a,'second_indicator':b,
                        'status':'CONFIRMED_PIVOTS_NOT_CONFIRMED_REVERSAL'})
    return sorted(result,key=lambda x:(x['available_at_bar'],x['indicator']))
