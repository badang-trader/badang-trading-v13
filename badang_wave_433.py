"""Non-predictive Elliott impulse *candidates* from confirmed candle swing pivots.
No claim of unique wave count, win probability, or execution authorization.
"""
from math import isfinite

def wave_candidates(bars, atr, span=3):
    if len(bars)<55 or not isinstance(atr,(int,float)) or not isfinite(atr) or atr<=0:
        return {'status':'INSUFFICIENT','candidates':[],'note':'확정봉 55개 및 ATR 필요'}
    recent=bars[-180:]
    raw=[]
    for i in range(span,len(recent)-span):
        seg=recent[i-span:i+span+1]
        if recent[i]['high']>max(x['high'] for j,x in enumerate(seg) if j!=span):raw.append({'kind':'H','price':recent[i]['high'],'index':i,'time_ms':recent[i]['start_ms']})
        if recent[i]['low']<min(x['low'] for j,x in enumerate(seg) if j!=span):raw.append({'kind':'L','price':recent[i]['low'],'index':i,'time_ms':recent[i]['start_ms']})
    # Alternate pivots, retain most extreme pivot of consecutive same type.
    alt=[]
    for p in sorted(raw,key=lambda x:x['index']):
        if alt and p['kind']==alt[-1]['kind']:
            if (p['kind']=='H' and p['price']>alt[-1]['price']) or (p['kind']=='L' and p['price']<alt[-1]['price']):alt[-1]=p
        elif not alt or abs(p['price']-alt[-1]['price'])>=atr*.35:alt.append(p)
    candidates=[]
    for n in (4,6):
        for i in range(max(0,len(alt)-16),len(alt)-n+1):
            seq=alt[i:i+n]
            for side in ('UP','DOWN'):
                kinds=['L','H']*(n//2) if side=='UP' else ['H','L']*(n//2)
                if [p['kind'] for p in seq]!=kinds:continue
                p=[x['price'] for x in seq]
                if n==4:
                    valid=(p[2]>p[0] and p[3]>p[1]) if side=='UP' else (p[2]<p[0] and p[3]<p[1])
                    if not valid:continue
                    label='3파 진행 가능성 (초기 상승/하락 구조)' if side=='UP' else '하락 3파 진행 가능성 (초기 하락 구조)'
                    invalid=p[2]
                else:
                    valid=(p[2]>p[0] and p[3]>p[1] and p[4]>p[2] and p[5]>p[3]) if side=='UP' else (p[2]<p[0] and p[3]<p[1] and p[4]<p[2] and p[5]<p[3])
                    if not valid:continue
                    label='5파 후보 구조 (확정 아님)' if side=='UP' else '하락 5파 후보 구조 (확정 아님)'
                    invalid=p[4]
                candidates.append({'direction':side,'label':label,'pivot_prices':[round(x,8) for x in p],
                                   'last_pivot_ms':seq[-1]['time_ms'],'invalid_below_above':round(invalid,8),
                                   'invalidation_rule':'종가가 기준 아래로 이탈 시 재검토' if side=='UP' else '종가가 기준 위로 이탈 시 재검토',
                                   'pivot_count':n})
    candidates.sort(key=lambda c:(c['last_pivot_ms'],c['pivot_count']),reverse=True)
    return {'status':'CANDIDATES' if candidates else 'NO_VALID_PATTERN','candidates':candidates[:3],
            'pivots_used':len(alt),'note':'국소 고저점 기반 단순 파동 가설. 3파/5파 확정, 중첩 파동·피보나치·거래량 검증 아님. 무효화 가격은 후보 구조의 참고 기준.'}
