"""Read-only research collection; saves OKX candles and provenance as CI artifacts.

No credentials, order access or performance claims. Fail visibly if the exchange
cannot be reached. Data files are not committed to the repository.
"""
import json,os,time
from pathlib import Path
from badang_okx_history import fetch_okx_closed_history

def main():
    out=Path(os.environ.get('BADANG_RESEARCH_OUTPUT','research-output'))
    out.mkdir(parents=True,exist_ok=True)
    summary={'collected_at_ms':int(time.time()*1000),'markets':[],
             'errors':[],'status':'INCOMPLETE'}
    for symbol in ('BTC','ETH'):
        for frame in ('15m','30m','1H','4H','1D'):
            key=f'{symbol}_{frame}'
            try:
                result=fetch_okx_closed_history(symbol,frame,pages=3)
                (out/f'{key}.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
                summary['markets'].append({'market':key,**result['provenance']})
            except Exception as exc:
                summary['errors'].append({'market':key,'error_type':type(exc).__name__,
                                          'message':str(exc)[:250]})
    summary['status']='COMPLETE' if len(summary['markets'])==10 else 'INCOMPLETE'
    (out/'manifest.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    if summary['status']!='COMPLETE':raise SystemExit(1)

if __name__=='__main__':main()
