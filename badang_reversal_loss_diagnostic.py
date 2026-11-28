"""Read-only reversal loss attribution; descriptive only, no optimized rules."""
import json
from collections import Counter
from pathlib import Path

def summarize_loss_reasons(cases):
    output={}
    for kind in ('early','confirmed'):
        by_part={}
        for part in ('TRAIN','HOLDOUT'):
            trades=[t for case in cases for t in case['reversal_backtest'][kind]['trades']
                    if t['partition']==part]
            done=[t for t in trades if t['net_return'] is not None]
            reasons=Counter(t['exit_reason'] for t in done)
            losses=[t for t in done if t['net_return']<0]
            risk_buckets={}
            for name,low,high in (('UNDER_0_5_PCT',0,0.005),('FROM_0_5_TO_2_PCT',0.005,0.02),('AT_LEAST_2_PCT',0.02,float('inf'))):
                group=[t for t in done if low<=abs(t['entry']-t['stop'])/t['entry']<high]
                risk_buckets[name]={'completed':len(group),'stops':sum(t['exit_reason']=='STOP' for t in group),
                    'mean_net_return':sum(t['net_return'] for t in group)/len(group) if group else None}
            by_part[part]={
                'completed':len(done),'censored':len(trades)-len(done),
                'entry_to_stop_distance_buckets':risk_buckets,
                'stops':reasons['STOP'],'targets':reasons['TARGET'],
                'losing_trades':len(losses),
                'losses_from_stops':sum(t['exit_reason']=='STOP' for t in losses),
                'mean_net_return':sum(t['net_return'] for t in done)/len(done) if done else None,
                'caveat':'Stop frequency does not establish the cause; trend, volatility and pivot delay require separate tests'}
        output[kind]=by_part
    return {'research_only':True,'strategy_loss_attribution':output,
            'not_original_badang_score':True,'historical_oi_cvd':'NOT_AVAILABLE'}

def main():
    folder=Path('research-output')
    data=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))
    result=summarize_loss_reasons(data['cases'])
    (folder/'bitget_reversal_loss_diagnostic.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
