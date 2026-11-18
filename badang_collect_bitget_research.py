"""Read-only Bitget primary and OKX secondary historical research.

Never mix exchange candles into a single signal; preserve each exchange's
independent provenance. Missing exchange history is an explicit failure.
"""
import json,os,time
from pathlib import Path
from badang_bitget_history import fetch_bitget_closed_history
from badang_okx_history import fetch_okx_closed_history

def main():
    out=Path(os.environ.get('BADANG_RESEARCH_OUTPUT','research-output'))
    out.mkdir(parents=True,exist_ok=True)
    manifest={'collected_at_ms':int(time.time()*1000),'markets':[],
              'errors':[],'status':'INCOMPLETE','primary':'BITGET','secondary':'OKX'}
    for symbol in ('BTC','ETH'):
        for frame in ('15m','30m','1H','4H','1D'):
            key=f'{symbol}_{frame}'
            try:
                result=fetch_bitget_closed_history(symbol,frame,pages=8)
                (out/f'bitget_{key}.json').write_text(json.dumps(result),encoding='utf-8')
                manifest['markets'].append({'market':key,**result['provenance']})
            except Exception as exc:
                manifest['errors'].append({'market':key,'type':type(exc).__name__,
                                           'message':str(exc)[:250]})
    manifest['status']='COMPLETE' if len(manifest['markets'])==10 else 'INCOMPLETE'
    (out/'bitget_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    comparisons=[]
    for m in manifest['markets']:
        key=m['market']
        other=out/f'{key}.json'
        if not other.exists():continue
        bitget=json.loads((out/f'bitget_{key}.json').read_text())['candles']
        okx=json.loads(other.read_text())['candles']
        o={int(row[0]):float(row[4]) for row in okx}
        overlap=[(float(row[4]),o[int(row[0])]) for row in bitget if int(row[0]) in o]
        comparisons.append({'market':key,'matched_closed_timestamps':len(overlap),
            'mean_abs_close_difference_pct':(
                sum(abs(a-b)/b*100 for a,b in overlap)/len(overlap) if overlap else None),
            'comparison':'SAME_TIMESTAMP_SEPARATE_EXCHANGES'})
    (out/'bitget_okx_comparison.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
    print(json.dumps({'bitget':manifest,'comparisons':comparisons},ensure_ascii=False))
    if manifest['status']!='COMPLETE':raise SystemExit(1)

if __name__=='__main__':main()
