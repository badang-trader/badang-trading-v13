"""Independent research artifact consistency gate; no account or orders."""
import json
from pathlib import Path

def validate_reversal_artifact(payload):
    if payload.get('primary_exchange')!='BITGET':raise ValueError('not Bitget research')
    cases=payload.get('cases',[])
    keys={(c['symbol'],c['timeframe']) for c in cases}
    if len(cases)!=10 or len(keys)!=10:raise ValueError('expected 10 distinct markets')
    result={'markets':len(cases),'strategies':{},'censored':0}
    for c in cases:
        for key in ('early','confirmed'):
            back=c['reversal_backtest'][key]
            for part in ('TRAIN','HOLDOUT'):
                for side in ('LONG','SHORT'):
                    label=part+'_'+side
                    group=back['summary'][label]
                    trades=[t for t in back['trades'] if t['partition']==part and t['side']==side]
                    done=[t for t in trades if t['net_return'] is not None]
                    censored=[t for t in trades if t['net_return'] is None]
                    if len(trades)!=group['signals_traded'] or len(done)!=group['completed_trades'] or len(censored)!=group['censored']:
                        raise ValueError('trade count mismatch '+str((c['symbol'],c['timeframe'],key,label)))
                    if any(t['crosses_split'] for t in trades):raise ValueError('split contamination')
                    if any(t['exit_reason'] not in ('END_OF_DATA','END_OF_PARTITION') for t in censored):
                        raise ValueError('invalid censor reason')
                    result['censored']+=len(censored)
                    k=key+'_'+part
                    slot=result['strategies'].setdefault(k,{'completed':0,'long':0,'short':0,'wins':0,'net_sum':0.})
                    slot['completed']+=len(done)
                    slot[side.lower()]+=len(done)
                    slot['wins']+=sum(t['net_return']>0 for t in done)
                    slot['net_sum']+=sum(t['net_return'] for t in done)
    for slot in result['strategies'].values():
        n=slot['completed']
        slot['win_rate']=slot['wins']/n if n else None
        slot['mean_net_return']=slot['net_sum']/n if n else None
        slot['not_portfolio_return']=True
    return result

def main():
    folder=Path('research-output')
    data=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))
    summary=validate_reversal_artifact(data)
    (folder/'bitget_reversal_consistency.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))

if __name__=='__main__':main()
