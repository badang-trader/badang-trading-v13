"""Read-only Bitget USDT perpetual closed-candle research downloader.

Uses Bitget public mix history-candles; no account credentials or orders.
A response is not considered validated until its OHLCV and timestamp audit passes.
"""
import time
import requests
from badang_historical_integrity import FRAME_MS,audit_historical_candles

URL='https://api.bitget.com/api/v2/mix/market/history-candles'
SYMBOLS={'BTC':'BTCUSDT','ETH':'ETHUSDT'}
BARS={'15m':'15m','30m':'30m','1H':'1H','4H':'4H','1D':'1Dutc'}

def fetch_bitget_closed_history(symbol,timeframe,*,pages=3,session=None,now_ms=None):
    if symbol not in SYMBOLS or timeframe not in BARS:
        raise ValueError('unsupported Bitget market')
    if not isinstance(pages,int) or isinstance(pages,bool) or not 1<=pages<=20:
        raise ValueError('pages must be 1..20')
    now_ms=int(time.time()*1000) if now_ms is None else now_ms
    step=FRAME_MS[timeframe]
    get=(session or requests.Session()).get
    records={}
    cursor=(now_ms//step)*step
    for _ in range(pages):
        params={'symbol':SYMBOLS[symbol],'productType':'USDT-FUTURES',
                'granularity':BARS[timeframe],'limit':'100','endTime':str(cursor)}
        response=get(URL,params=params,timeout=15)
        response.raise_for_status()
        payload=response.json()
        if not isinstance(payload,dict) or str(payload.get('code'))!='00000' or not isinstance(payload.get('data'),list):
            raise ValueError('invalid Bitget history response')
        if not payload['data']:break
        oldest=None
        for item in payload['data']:
            if not isinstance(item,list) or len(item)<6:
                raise ValueError('invalid Bitget candle')
            ts=int(item[0])
            if oldest is None or ts<oldest:oldest=ts
            if ts+step>now_ms:continue
            # Bitget OHLCV: timestamp, open, high, low, close, baseVolume, quoteVolume.
            row=[ts]+[float(v) for v in item[1:6]]
            if ts in records and records[ts]!=row:
                raise ValueError('conflicting Bitget duplicate')
            records[ts]=row
        if oldest is None or oldest>=cursor:
            raise ValueError('Bitget pagination failed to move backward')
        cursor=oldest
    rows=[records[ts] for ts in sorted(records)]
    provenance=audit_historical_candles(rows,timeframe,asof_ms=now_ms)
    provenance.update({'source':'BITGET_PUBLIC_HISTORY_API','instrument':SYMBOLS[symbol],
        'productType':'USDT-FUTURES','endpoint':URL,'volume_unit':'base_asset',
        'pages_requested':pages,'collection_timestamp_ms':now_ms})
    return {'candles':rows,'provenance':provenance}
