"""Read-only, fixed-bin causal context audit for reversal trades.

All context is computed using candles closed no later than the signal bar.
Buckets are descriptive, not tuned thresholds or evidence of causality.
"""
import json
from collections import defaultdict
from pathlib import Path

def signal_context(rows, signal_bar, side, entry, stop):
    if signal_bar < 20 or signal_bar >= len(rows):
        return None
    closes=[float(x[4]) for x in rows]
    # EMA20 as-of the closed signal candle; no future bars.
    ema=closes[0]
    alpha=2/21
    for v in closes[1:signal_bar+1]:
        ema=alpha*v+(1-alpha)*ema
    trend='WITH_EMA20' if ((closes[signal_bar]>=ema)==(side=='LONG')) else 'AGAINST_EMA20'
    tr=[]
    for i in range(signal_bar-13,signal_bar+1):
        h,l,prev=float(rows[i][2]),float(rows[i][3]),float(rows[i-1][4])
        tr.append(max(h-l,abs(h-prev),abs(l-prev)))
    atr=sum(tr)/len(tr)
    atr_pct=atr/closes[signal_bar]
    return {'trend':trend,'atr_pct':atr_pct,
            'atr_band':'LOW' if atr_pct<0.01 else 'MID' if atr_pct<0.03 else 'HIGH',
            'stop_pct':abs(entry-stop)/entry}

def diagnose(cases, histories):
    result=[]
    for case in cases:
        symbol,frame=case['symbol'],case['timeframe']
        rows=histories[(symbol,frame)]
        for strategy in ('early','confirmed'):
            for part in ('TRAIN','HOLDOUT'):
                trades=[t for t in case['reversal_backtest'][strategy]['trades']
                        if t['partition']==part and t['net_return'] is not None]
                groups=defaultdict(list)
                for t in trades:
                    ctx=signal_context(rows,t['signal_bar'],t['side'],t['entry'],t['stop'])
                    if ctx is None:continue
                    groups['trend:'+ctx['trend']].append(t)
                    groups['atr:'+ctx['atr_band']].append(t)
                    groups['side:'+t['side']].append(t)
                    groups['stop:'+('UNDER_0_5' if ctx['stop_pct']<.005 else 'FROM_0_5_TO_2' if ctx['stop_pct']<.02 else 'AT_LEAST_2')].append(t)
                for label,ts in sorted(groups.items()):
                    result.append({'symbol':symbol,'timeframe':frame,'strategy':strategy,
                        'partition':part,'group':label,'completed':len(ts),
                        'stops':sum(t['exit_reason']=='STOP' for t in ts),
                        'wins':sum(t['net_return']>0 for t in ts),
                        'mean_net_return':sum(t['net_return'] for t in ts)/len(ts),
                        'small_sample':len(ts)<20})
    return {'status':'DESCRIPTIVE_NOT_CAUSAL','uses_future_candles_for_context':False,
            'higher_timeframe_alignment':'NOT_TESTED','pivot_delay':'NOT_TESTED',
            'post_stop_rebound':'NOT_TESTED','original_badang_score':'NOT_EVALUATED',
            'historical_oi_cvd':'NOT_AVAILABLE','groups':result}

def main():
    folder=Path('research-output')
    payload=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))
    histories={}
    for case in payload['cases']:
        k=(case['symbol'],case['timeframe'])
        histories[k]=json.loads((folder/('bitget_'+k[0]+'_'+k[1]+'.json')).read_text(encoding='utf-8'))['candles']
    output=diagnose(payload['cases'],histories)
    (folder/'bitget_reversal_causal_context.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({'groups':len(output['groups']),'status':output['status']}))

if __name__=='__main__':main()
