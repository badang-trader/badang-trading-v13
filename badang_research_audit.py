"""Research-only audit on real downloaded OKX candles, not a trade backtest.

No historical order-flow feed is available; scores requiring it are explicitly
unverified. Computes genuine existing BADANG indicators for the latest 205+ bars.
"""
import json
from pathlib import Path
from badang_historical_signal_adapter import analyze_closed_prefix

def main():
    folder=Path('research-output')
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    reports=[]
    for market in manifest['markets']:
        name=market['market']
        payload=json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
        rows=payload['candles']
        result=analyze_closed_prefix(rows)
        if result is None: raise ValueError(name+' insufficient indicator history')
        reports.append({'market':name,'bars':len(rows),
                        'latest_close_timestamp_ms':rows[-1][0],
                        'last_close':rows[-1][4],
                        'trend':result['trend'],'rsi':result['rsi'],
                        'macd':result['macd'],'macd_signal':result['macd_signal'],
                        'atr':result['atr'],'divergence':result['divergence'],
                        'volume_ratio':result['volume_ratio'],
                        'flow':'NOT_COLLECTED','score':'NOT_VERIFIED',
                        'backtest':'NOT_RUN_NO_HISTORICAL_FLOW'})
    report={'status':'REAL_OKX_INDICATORS_ONLY','markets':reports,
            'actual_backtest_performance':'NOT_VERIFIED',
            'note':'Historical CVD/trade direction/OI not collected; no fabricated 80+ scores'}
    (folder/'real_indicators_audit.json').write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
