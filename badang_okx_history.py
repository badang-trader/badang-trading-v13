"""Read-only OKX history downloader; no credentials, orders or fabricated data.

Use on a network-enabled, authorized research machine. Captures only confirmed
candles; refuses gaps and mismatched timestamps rather than interpolating.
"""
import time
import requests
from badang_historical_integrity import FRAME_MS,audit_historical_candles

BARS={'15m':'15m','30m':'30m','1H':'1H','4H':'4H','1D':'1Dutc'}
SYMBOLS={'BTC':'BTC-USDT-SWAP','ETH':'ETH-USDT-SWAP'}
URL='https://www.okx.com/api/v5/market/history-candles'

def fetch_okx_closed_history(symbol,timeframe,*,pages=3,session=None,now_ms=None):
    if symbol not in SYMBOLS or timeframe not in BARS: raise ValueError('unsupported market')
    if not isinstance(pages,int) or isinstance(pages,bool) or not 1<=pages<=20:
        raise ValueError('pages must be 1..20')
    now_ms=int(time.time()*1000) if now_ms is None else now_ms
    step=FRAME_MS[timeframe]
    get=(session or requests.Session()).get
    all_rows={}
    after=None
    for _ in range(pages):
        params={'instId':SYMBOLS[symbol],'bar':BARS[timeframe],'limit':'100'}
        if after is not None:params['after']=str(after)
        response=get(URL,params=params,timeout=15)
        response.raise_for_status()
        data=response.json()
        if not isinstance(data,dict) or str(data.get('code'))!='0' or not isinstance(data.get('data'),list):
            raise ValueError('invalid OKX response')
        if not data['data']:break
        oldest=None
        for item in data['data']:
            if not isinstance(item,list) or len(item)<9 or item[8] not in ('0','1'):
                raise ValueError('invalid OKX candle format')
            ts=int(item[0])
            if oldest is None or ts<oldest:oldest=ts
            if item[8]=='0':continue
            if ts+step>now_ms:raise ValueError('OKX confirmed bar closes in future')
            row=[ts]+[float(v) for v in item[1:6]]
            if ts in all_rows and all_rows[ts]!=row:
                raise ValueError('conflicting duplicate OKX candle')
            all_rows[ts]=row
        if oldest is None or (after is not None and oldest>=after):
            raise ValueError('OKX pagination did not move backward')
        after=oldest
    rows=[all_rows[k] for k in sorted(all_rows)]
    report=audit_historical_candles(rows,timeframe,asof_ms=now_ms)
    report.update({'source':'OKX_PUBLIC_HISTORY_API','instrument':SYMBOLS[symbol],
                   'volume_unit':'contracts','endpoint':URL,'pages_requested':pages})
    return {'candles':rows,'provenance':report}
