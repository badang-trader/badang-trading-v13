"""Research-only simultaneous exposure diagnostic; never a portfolio PnL claim.

Intervals use actual candle timestamps per timeframe; a trade is active from
entry candle open until exit candle close (conservative overlap bound).
"""
import json
from collections import defaultdict
from pathlib import Path
from badang_historical_integrity import FRAME_MS

def exposure_diagnostic(cases,kind):
    if kind not in ('early','confirmed'):raise ValueError('invalid strategy')
    intervals=[]
    for case in cases:
        step=FRAME_MS[case['timeframe']]
        rows=case['reversal_backtest'][kind]['trades']
        # Candle timestamp is the open time; each instrument retains its own clock.
        # Reconstruct absolute time from integrity start and bar index.
        start=case['integrity']['start_ms']
        for trade in rows:
            a=start+trade['entry_bar']*step
            b=start+(trade['exit_bar']+1)*step
            if b<=a:raise ValueError('invalid trade interval')
            intervals.append((a,b,case['symbol'],case['timeframe'],trade['side']))
    events=[]
    for i,(a,b,symbol,frame,side) in enumerate(intervals):
        events.append((a,1,i));events.append((b,-1,i))
    events.sort(key=lambda x:(x[0],x[1]))
    active=set();maximum=0;max_by_symbol=defaultdict(int)
    cross_timeframe_pairs=0
    for i,(a,b,sym,frame,side) in enumerate(intervals):
        for aa,bb,ss,ff,_ in intervals[:i]:
            if sym==ss and frame!=ff and max(a,aa)<min(b,bb):
                cross_timeframe_pairs+=1
    for _,change,i in events:
        if change<0:active.remove(i)
        else:active.add(i)
        maximum=max(maximum,len(active))
        by_symbol=defaultdict(int)
        for j in active:by_symbol[intervals[j][2]]+=1
        for symbol,n in by_symbol.items():max_by_symbol[symbol]=max(max_by_symbol[symbol],n)
    return {'strategy':kind.upper(),'trade_intervals':len(intervals),
            'maximum_simultaneous_timeframe_positions':maximum,
            'max_simultaneous_by_symbol':dict(max_by_symbol),
            'same_symbol_cross_timeframe_overlap_pairs':cross_timeframe_pairs,
            'capital_allocation':'NOT_MODELED',
            'portfolio_return':'NOT_COMPUTABLE_WITHOUT_SIZING_AND_EXECUTION',
            'research_only':True}

def main():
    folder=Path('research-output')
    data=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))
    result={'early':exposure_diagnostic(data['cases'],'early'),
            'confirmed':exposure_diagnostic(data['cases'],'confirmed')}
    (folder/'bitget_timeframe_exposure.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
