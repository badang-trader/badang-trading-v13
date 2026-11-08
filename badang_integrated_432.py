"""Multi-timeframe evidence summary; never a trading authorization or claimed win rate."""
from math import isfinite

WEIGHTS={'15m':1,'30m':1.5,'1H':2,'4H':2.5}

def build_report(depth):
    frames=depth.get('timeframes',{})
    votes=[]; all_levels=[]; gaps=[]
    for tf,weight in WEIGHTS.items():
        v=frames.get(tf)
        if not v: gaps.append(tf+': 조회 실패'); continue
        q=v.get('quality',{})
        if v.get('analysis_status')!='VALID':
            gaps.append(tf+': 자료 제한');continue
        e20,e50,e200=(v.get('ema20'),v.get('ema50'),v.get('ema200'))
        px=v.get('current_price');atr=v.get('atr14')
        if not all(isinstance(x,(int,float)) and isfinite(x) and x>0 for x in (e20,e50,e200,px,atr)):
            gaps.append(tf+': 지표 미확인');continue
        if e20>e50>e200 and px>e20:direction='상승 정렬'
        elif e20<e50<e200 and px<e20:direction='하락 정렬'
        elif px<e200:direction='장기 하락 속 혼조'
        elif px>e200:direction='장기 상승 속 혼조'
        else:direction='혼조'
        votes.append({'timeframe':tf,'direction':direction,'weight':weight,'price':px,'atr':atr})
        for key,kind in [('supports','지지'),('resistances','저항')]:
            for level in (v.get('levels') or {}).get(key,[]):
                lp=level.get('price'); touches=level.get('touches',0)
                if not isinstance(lp,(int,float)) or not isfinite(lp):continue
                # Rank by multi-timeframe weight, swing touches and proximity, not claimed probability.
                score=weight*(1+min(max(touches,0),5)*.25)/(1+abs(lp-px)/max(atr,1))
                all_levels.append({'timeframe':tf,'kind':kind,'price':round(lp,8),'touches':touches,'rank_score':round(score,3)})
    def cluster(kind):
        items=sorted([x for x in all_levels if x['kind']==kind],key=lambda z:z['price'])
        if not items:return []
        reference=next((v for v in frames.values() if v.get('atr14') and v.get('current_price')),None)
        tolerance=max((reference['atr14']*.4 if reference else 0), (reference['current_price']*.0005 if reference else 0))
        groups=[]
        for x in items:
            group=next((g for g in groups if abs(g['price']-x['price'])<=tolerance),None)
            if group:
                total=group['weight']+x['rank_score']
                group['price']=(group['price']*group['weight']+x['price']*x['rank_score'])/total if total else group['price']
                group['weight']=total;group['sources'].append(x['timeframe']);group['touches']+=x['touches']
            else:groups.append({'price':x['price'],'weight':x['rank_score'],'sources':[x['timeframe']],'touches':x['touches']})
        return [{'price':round(g['price'],5),'strength_index':round(g['weight'],2),'timeframes':sorted(set(g['sources'])),'pivot_count':g['touches']} for g in sorted(groups,key=lambda g:-g['weight'])[:3]]
    bullish=sum(v['weight'] for v in votes if v['direction']=='상승 정렬')
    bearish=sum(v['weight'] for v in votes if v['direction']=='하락 정렬')
    return {'frame_trends':votes,'bullish_weight':bullish,'bearish_weight':bearish,
            'trend_reading':'상승 정렬 우세' if bullish>bearish else '하락 정렬 우세' if bearish>bullish else '혼조/판정 유보',
            'key_supports':cluster('지지'),'key_resistances':cluster('저항'),
            'limitations':gaps+['지지·저항 강도는 상대 순위이며 지지 성공 확률이 아님',
                '실시간 체결 CVD/OI 변화와 진행봉은 이 점수에 반영되지 않음',
                '엘리엇파동 3파·5파 확정 판별은 구현·검증되지 않음'],
            'signal':'분석 참고 전용 · 자동 진입 판단 아님'}
