"""Audit historical multi-timeframe eligibility on genuine OKX data.

No historical order-flow was collected. This program intentionally does not
fabricate BUY/SELL states, scores, signals, trades or win rates.
"""
import json
from pathlib import Path
from badang_historical_integrity import FRAME_MS,audit_historical_candles
from badang_historical_signal_adapter import score_historical_prefixes

MODES={'scalp':('15m','30m','1H'),'swing':('1H','4H','1D')}

def aligned_prefix(rows,frame,asof):
    step=FRAME_MS[frame]
    return [r for r in rows if int(r[0])+step<=asof]

def inspect_market(market_data,mode):
    lower,setup,higher=MODES[mode]
    step=FRAME_MS[setup]
    rows=market_data[setup]
    counts={'setup_bars':len(rows),'eligible_three_frame_prefixes':0,
            'missing_history':0,'historical_flow_missing':0,
            'signals':0,'trades':0}
    for idx in range(204,len(rows)-1):
        asof=int(rows[idx][0])+step
        prefixes={f:aligned_prefix(market_data[f],f,asof)
                  for f in (lower,setup,higher)}
        if any(len(prefixes[f])<205 for f in (lower,setup,higher)):
            counts['missing_history']+=1
            continue
        counts['eligible_three_frame_prefixes']+=1
        result=score_historical_prefixes(
            prefixes[setup],prefixes[lower],prefixes[higher],mode,
            setup_frame=setup,lower_frame=lower,higher_frame=higher)
        if result is None or result['status']!='HISTORICAL_FLOW_MISSING':
            raise ValueError('unexpected historical signal without verified flow')
        counts['historical_flow_missing']+=1
    return counts

def main():
    root=Path('research-output')
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='COMPLETE':raise ValueError('incomplete OKX collection')
    report={'status':'HISTORICAL_FLOW_NOT_AVAILABLE','markets':[],
            'historical_badang_scores':'NOT_CALCULATED',
            'actual_strategy_backtest':'NOT_RUN',
            'reason':'No time-stamped authenticated historical order flow'}
    for symbol in ('BTC','ETH'):
        frames={}
        for frame in ('15m','30m','1H','4H','1D'):
            record=json.loads((root/f'{symbol}_{frame}.json').read_text(encoding='utf-8'))
            rows=record['candles']
            audit_historical_candles(rows,frame,asof_ms=manifest['collected_at_ms'])
            frames[frame]=rows
        for mode in MODES:
            report['markets'].append({'symbol':symbol,'mode':mode,
                                      **inspect_market(frames,mode)})
    (root/'historical_signal_readiness.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
