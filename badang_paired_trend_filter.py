"""Paired, research-only comparison of all completed trade opportunities.

Returns are per-trade, NOT an equity curve or portfolio backtest. A skipped
trade has zero opportunity return, not a claim that capital was redeployed.
"""
from badang_reversal_multiframe_alignment import alignment

FILTERS=('EMA20','EMA50','EMA200','higher')

def compare(cases,histories):
    rows=[]
    for case in cases:
        symbol=case['symbol']; frame=case['timeframe']
        for strategy in ('early','confirmed'):
            for partition in ('TRAIN','HOLDOUT'):
                trades=[t for t in case['reversal_backtest'][strategy]['trades']
                        if t['partition']==partition and t['net_return'] is not None]
                contexts=[alignment(histories,symbol,frame,t['signal_bar'],t['side']) for t in trades]
                for metric in FILTERS:
                    known=[(t,c[metric]) for t,c in zip(trades,contexts)
                           if c.get(metric) in ('WITH','AGAINST')]
                    included=[t for t,v in known if v=='WITH']
                    excluded=[t for t,v in known if v=='AGAINST']
                    def stats(ts):
                        return {'count':len(ts),
                                'sum_net_trade_returns':sum(t['net_return'] for t in ts),
                                'mean_net_trade_return':sum(t['net_return'] for t in ts)/len(ts) if ts else None,
                                'stops':sum(t['exit_reason']=='STOP' for t in ts),
                                'wins':sum(t['net_return']>0 for t in ts)}
                    rows.append({'symbol':symbol,'timeframe':frame,'strategy':strategy,
                        'partition':partition,'filter':metric,
                        'completed_opportunities':len(trades),
                        'known_opportunities':len(known),
                        'unknown_opportunities':len(trades)-len(known),
                        'baseline_known':stats([t for t,_ in known]),
                        'included':stats(included),'excluded':stats(excluded),
                        'filtered_return_per_known_opportunity':
                            sum(t['net_return'] for t in included)/len(known) if known else None,
                        'not_portfolio_backtest':True,
                        'small_included_sample':len(included)<20})
    return {'status':'DESCRIPTIVE_NOT_CAUSAL','research_only':True,
        'same_opportunities':True,'new_nonoverlapping_period_verified':False,
        'no_historical_oi_cvd':True,'rows':rows}

def main():
    import json
    from pathlib import Path
    folder=Path('research-output')
    cases=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))['cases']
    histories={(c['symbol'],c['timeframe']):json.loads(
        (folder/('bitget_'+c['symbol']+'_'+c['timeframe']+'.json')).read_text(encoding='utf-8'))['candles']
        for c in cases}
    output=compare(cases,histories)
    (folder/'bitget_paired_trend_filter.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print('paired trend groups:',len(output['rows']))

if __name__=='__main__':main()
