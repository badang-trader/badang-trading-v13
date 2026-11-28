"""Causal historical pivot audit on real OKX OHLCV, research-only.

A pivot at index i is not available until index i+right closes. Equal highs/lows
are excluded to avoid ambiguous turning points. Pattern labels are hypotheses,
not confirmed Elliott classifications.
"""
import json
from pathlib import Path

def confirmed_pivots(rows,left=3,right=3):
    if not isinstance(left,int) or not isinstance(right,int) or min(left,right)<1:
        raise ValueError('positive confirmation windows required')
    found=[]
    for i in range(left,len(rows)-right):
        highs=[float(x[2]) for x in rows[i-left:i+right+1]]
        lows=[float(x[3]) for x in rows[i-left:i+right+1]]
        hi=float(rows[i][2]);lo=float(rows[i][3])
        if highs.count(hi)==1 and hi==max(highs):
            found.append({'pivot_bar':i,'confirmed_at_bar':i+right,
                          'type':'HIGH','price':hi,'timestamp_ms':rows[i][0]})
        if lows.count(lo)==1 and lo==min(lows):
            found.append({'pivot_bar':i,'confirmed_at_bar':i+right,
                          'type':'LOW','price':lo,'timestamp_ms':rows[i][0]})
    return sorted(found,key=lambda p:(p['confirmed_at_bar'],p['pivot_bar']))

def main():
    folder=Path('research-output')
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    cases=[]
    for m in manifest['markets']:
        name=m['market']
        rows=json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))['candles']
        pivots=confirmed_pivots(rows)
        if any(p['confirmed_at_bar']>=len(rows) for p in pivots):
            raise ValueError('unconfirmed pivot detected')
        cases.append({'market':name,'confirmed_pivots':len(pivots),
                      'sample_pivots':pivots[:5],
                      'elliott_pattern':'NOT_CLASSIFIED',
                      'main_alternative_scenarios':'NOT_VALIDATED',
                      'invalidation':'NOT_VALIDATED'})
    result={'status':'CAUSAL_PIVOT_EVENTS_ONLY','markets':cases,
            'elliott_impulse_abc_complex_diagonal':'NOT_VALIDATED'}
    (folder/'confirmed_pivot_audit.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
