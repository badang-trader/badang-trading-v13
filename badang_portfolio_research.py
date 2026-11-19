"""Research-only chronological portfolio replay of completed, precomputed trades.

No exchange calls, no orders, no liquidation simulation. Portfolio sizing is
fixed fractional margin; the underlying trade returns already include fees.
Missing/unfinished exits are excluded and counted, never marked as winners.
"""
import json
from pathlib import Path
from badang_reversal_multiframe_alignment import alignment
from badang_portfolio_events import allocate,realized_path
from badang_historical_integrity import FRAME_MS

def simulate(cases,histories,*,strategy='early',partition='HOLDOUT',
             filter_name=None,initial_capital=10000.0,
             margin_fraction=.05,leverage=2.0,max_total_margin_fraction=.30):
    if initial_capital<=0 or not 0<margin_fraction<=1 or leverage<=0 or not 0<max_total_margin_fraction<=1:
        raise ValueError('invalid capital, leverage or margin limits')
    if filter_name not in (None,'EMA20','EMA50','EMA200','higher'):
        raise ValueError('unknown filter')
    events=[];censored=0;unknown=0;filtered=0
    for case in cases:
        if case['symbol'] not in ('BTC','ETH'):continue
        key=(case['symbol'],case['timeframe'])
        candles=histories[key]
        for t in case['reversal_backtest'][strategy]['trades']:
            if t['partition']!=partition:continue
            if t['net_return'] is None:
                censored+=1;continue
            if filter_name is not None:
                status=alignment(histories,*key,t['signal_bar'],t['side']).get(filter_name)
                if status not in ('WITH','AGAINST'):
                    unknown+=1;continue
                if status=='AGAINST':
                    filtered+=1;continue
            entry_bar=t['entry_bar'];exit_bar=t['exit_bar']
            if not (0<=entry_bar<=exit_bar<len(candles)):
                raise ValueError('trade outside candle history')
            entry_ts=candles[entry_bar][0];exit_ts=candles[exit_bar][0]+FRAME_MS[key[1]]
            events.append({'entry_ts':entry_ts,'exit_ts':exit_ts,'key':key,'t':t})
    accepted_events,rejected=allocate(events,initial_capital,margin_fraction,
                                      leverage,max_total_margin_fraction)
    capital,max_dd=realized_path(accepted_events,initial_capital)
    accepted=len(accepted_events)
    max_positions=0;max_margin_used=0.
    for a in accepted_events:
        simultaneous=[b for b in accepted_events
                      if b['entry_ts']<=a['entry_ts']<=b['exit_ts']]
        max_positions=max(max_positions,len(simultaneous))
        max_margin_used=max(max_margin_used,sum(b['margin'] for b in simultaneous))
    return {'research_only':True,'model':'CLOSED_TRADE_EVENT_REPLAY_NOT_MARK_TO_MARKET',
        'liquidation_risk':'NOT_MODELED','same_timestamp_exit_margin_reuse':False,
        'strategy':strategy,'partition':partition,'filter':filter_name or 'NONE',
        'initial_capital':initial_capital,'ending_capital':capital,
        'realized_return':capital/initial_capital-1,
        'realized_event_drawdown':max_dd,'intratrade_drawdown':'NOT_MODELED',
        'accepted':accepted,'rejected_insufficient_margin':rejected,
        'filtered_out':filtered,'unknown_alignment':unknown,'censored':censored,
        'max_simultaneous_positions':max_positions,
        'max_reserved_margin':max_margin_used,'leverage':leverage,
        'margin_fraction':margin_fraction,'max_total_margin_fraction':max_total_margin_fraction}

def main():
    folder=Path('research-output')
    cases=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))['cases']
    histories={(c['symbol'],c['timeframe']):json.loads(
        (folder/('bitget_'+c['symbol']+'_'+c['timeframe']+'.json')).read_text(encoding='utf-8'))['candles']
        for c in cases}
    results=[simulate(cases,histories,strategy=s,partition=p,filter_name=f)
             for s in ('early','confirmed') for p in ('TRAIN','HOLDOUT')
             for f in (None,'EMA20','EMA50','EMA200','higher')]
    (folder/'bitget_portfolio_research.json').write_text(json.dumps(
        {'status':'EXPLORATORY_NO_LIQUIDATION_OR_MARK_TO_MARKET','results':results},indent=2),encoding='utf-8')
    print('portfolio scenarios:',len(results))

if __name__=='__main__':main()
