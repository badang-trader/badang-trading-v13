"""Read-only valuation of censored reversal trades at their last closed candle.

This is a per-trade diagnostic, NOT portfolio equity: censored positions have
not been allocated margin by the completed-trade-only portfolio simulator.
No future candles, fabricated exits, or exchange mark prices are used.
"""
import json
from collections import Counter
from pathlib import Path

FRAME_MS={'15m':900000,'30m':1800000,'1H':3600000,'4H':14400000,'1D':86400000}

def audit_censored(cases,histories,*,fee_each_side=.0006,slippage_each_side=.0003):
    if fee_each_side<0 or slippage_each_side<0:raise ValueError('negative cost')
    out=[]
    for case in cases:
        key=(case['symbol'],case['timeframe'])
        rows=histories[key]
        for strategy in ('early','confirmed'):
            backtest=case['reversal_backtest'][strategy]
            for t in backtest['trades']:
                if t['net_return'] is not None:continue
                i,j=t['entry_bar'],t['exit_bar']
                if not (0<=i<=j<len(rows)):raise ValueError('invalid censored bar indices')
                if t['exit_reason'] not in ('END_OF_DATA','END_OF_PARTITION'):
                    raise ValueError('unexpected censored exit reason')
                entry=float(t['entry'])
                if entry<=0:raise ValueError('invalid entry price')
                last_close=float(rows[j][4])
                side=t['side']
                if side not in ('LONG','SHORT'):raise ValueError('invalid side')
                sign=1 if side=='LONG' else -1
                gross=sign*(last_close-entry)/entry
                # Entry fee/slippage is known. Closing fee/slippage is only
                # a hypothetical cost, not a realized transaction.
                open_cost=fee_each_side+slippage_each_side
                out.append({'symbol':key[0],'timeframe':key[1],
                    'strategy':strategy,'partition':t['partition'],
                    'entry_ts_ms':int(rows[i][0]),
                    'last_closed_ts_ms':int(rows[j][0])+FRAME_MS[key[1]],
                    'entry_price':entry,'last_closed_price':last_close,
                    'side':side,'gross_unrealized_return':gross,
                    'net_of_entry_cost_proxy':gross-open_cost,
                    'hypothetical_round_trip_net_proxy':gross-2*open_cost,
                    'not_realized':True,'not_exchange_mark_price':True,
                    'not_allocated_to_portfolio':True,
                    'censored_reason':t['exit_reason'],
                    'observed_holding_ms':int(rows[j][0])+FRAME_MS[key[1]]-int(rows[i][0]),
                    'is_dataset_end_open_candidate':t['exit_reason']=='END_OF_DATA'})
    by_reason=Counter(p['censored_reason'] for p in out)
    by_partition=Counter(p['partition'] for p in out)
    return {'status':'CENSORED_LAST_CLOSED_PRICE_ONLY_NOT_PORTFOLIO_EQUITY',
        'count':len(out),'counts_by_reason':dict(sorted(by_reason.items())),
        'counts_by_partition':dict(sorted(by_partition.items())),
        'dataset_end_open_candidates':by_reason.get('END_OF_DATA',0),
        'partition_end_censored_not_current_positions':by_reason.get('END_OF_PARTITION',0),
        'positions':out,
        'warnings':['NO_EXIT_ASSUMED','NOT_LIQUIDATION_VERIFIED',
            'NO_MARGIN_ALLOCATION_FOR_CENSORED_TRADES',
            'HYPOTHETICAL_CLOSE_COST_NOT_REALIZED']}

def main():
    folder=Path('research-output')
    cases=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))['cases']
    histories={(c['symbol'],c['timeframe']):json.loads(
        (folder/f"bitget_{c['symbol']}_{c['timeframe']}.json").read_text(encoding='utf-8'))['candles']
        for c in cases}
    result=audit_censored(cases,histories)
    (folder/'bitget_censored_position_diagnostic.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('censored position diagnostics:',result['count'])

if __name__=='__main__':main()
