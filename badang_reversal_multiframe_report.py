"""Read-only actual Bitget trade groupings by causal EMA and higher timeframe."""
import json
from collections import defaultdict
from pathlib import Path
from badang_reversal_multiframe_alignment import alignment

def summarize(cases,histories):
    result=[]
    for case in cases:
        for strategy in ('early','confirmed'):
            for partition in ('TRAIN','HOLDOUT'):
                grouped=defaultdict(list)
                for t in case['reversal_backtest'][strategy]['trades']:
                    if t['partition']!=partition or t['net_return'] is None:continue
                    ctx=alignment(histories,case['symbol'],case['timeframe'],t['signal_bar'],t['side'])
                    for k,v in ctx.items():
                        if k.startswith('EMA') or k=='higher':
                            grouped[(k,v)].append(t)
                for (metric,status),ts in sorted(grouped.items()):
                    result.append({'symbol':case['symbol'],'timeframe':case['timeframe'],
                        'strategy':strategy,'partition':partition,'metric':metric,
                        'alignment':status,'completed':len(ts),
                        'stops':sum(t['exit_reason']=='STOP' for t in ts),
                        'wins':sum(t['net_return']>0 for t in ts),
                        'mean_net_return':sum(t['net_return'] for t in ts)/len(ts),
                        'small_sample':len(ts)<20})
    return {'research_only':True,'no_future_higher_candle':True,
        'not_a_trading_filter':True,'historical_oi_cvd':'NOT_AVAILABLE','groups':result}

def main():
    folder=Path('research-output')
    cases=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))['cases']
    histories={}
    for case in cases:
        key=(case['symbol'],case['timeframe'])
        histories[key]=json.loads((folder/('bitget_'+key[0]+'_'+key[1]+'.json')).read_text(encoding='utf-8'))['candles']
    output=summarize(cases,histories)
    (folder/'bitget_reversal_multiframe_alignment.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({'groups':len(output['groups']),'research_only':True}))

if __name__=='__main__':main()
