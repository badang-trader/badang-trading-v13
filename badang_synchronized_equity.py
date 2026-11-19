"""Research-only synchronized *closed-candle* multi-position equity observations.

Uses only exact common close timestamps; never interpolates a missing mark.
Not an intrabar equity bound, liquidation engine, or exchange mark-price replay.
Censored trades are excluded and explicitly counted.
"""
import json
from collections import Counter
from pathlib import Path
from badang_reversal_multiframe_alignment import alignment
from badang_portfolio_events import allocate,realized_path

FRAME_MS={'15m':900000,'30m':1800000,'1H':3600000,'4H':14400000,'1D':86400000}

def synchronized_marks(cases,histories,*,strategy='early',partition='HOLDOUT',
                       filter_name=None,initial_capital=10000.0,
                       margin_fraction=.05,leverage=2.,max_total_margin_fraction=.30):
    if initial_capital<=0 or not 0<margin_fraction<=1 or leverage<=0 or not 0<max_total_margin_fraction<=1:
        raise ValueError('invalid sizing')
    if filter_name not in (None,'EMA20','EMA50','EMA200','higher'):
        raise ValueError('invalid filter')
    trades=[];excluded=0;unknown=0;censored=0
    for case in cases:
        key=(case['symbol'],case['timeframe'])
        rows=histories[key];step=FRAME_MS[key[1]]
        for t in case['reversal_backtest'][strategy]['trades']:
            if t['partition']!=partition:continue
            if t['net_return'] is None:
                censored+=1;continue
            if filter_name:
                v=alignment(histories,*key,t['signal_bar'],t['side']).get(filter_name)
                if v not in ('WITH','AGAINST'):
                    unknown+=1;continue
                if v=='AGAINST':
                    excluded+=1;continue
            i,j=t['entry_bar'],t['exit_bar']
            if not 0<=i<=j<len(rows):raise ValueError('invalid trade bars')
            trades.append({'key':key,'t':t,'entry_ts':int(rows[i][0]),
                           'exit_ts':int(rows[j][0])+step,
                           'step':step,'rows':rows})
    accepted,rejected=allocate(trades,initial_capital,margin_fraction,leverage,
                               max_total_margin_fraction)
    final_cash,realized_dd=realized_path(accepted,initial_capital)
    # Exact close-time marks: a position is observed only at candle close,
    # and only before its recorded exit timestamp.
    close_maps={}
    for key,rows in histories.items():
        step=FRAME_MS[key[1]]
        close_maps[key]={int(r[0])+step:float(r[4]) for r in rows}
    timestamps=sorted({ts for a in accepted for ts in close_maps[a['key']]
                       if a['entry_ts']<ts<a['exit_ts']})
    observations=[];peak=initial_capital;worst_dd=0.;incomplete=0
    missing_by_frame=Counter();missing_position_marks=0;max_missing_at_timestamp=0
    for ts in timestamps:
        realized=initial_capital+sum(a['pnl'] for a in accepted if a['exit_ts']<ts)
        opened=[a for a in accepted if a['entry_ts']<ts<a['exit_ts']]
        marks=[];missing=[]
        for a in opened:
            mark=close_maps[a['key']].get(ts)
            if mark is None:
                missing.append(a['key']);continue
            direction=1 if a['t']['side']=='LONG' else -1
            pnl=a['exposure']*direction*(mark/float(a['t']['entry'])-1)
            marks.append((a,pnl))
        if missing:
            incomplete+=1
            missing_position_marks+=len(missing)
            max_missing_at_timestamp=max(max_missing_at_timestamp,len(missing))
            missing_by_frame.update(frame for _,frame in missing)
            continue
        equity=realized+sum(p for _,p in marks)
        locked=sum(a['margin'] for a in opened)
        peak=max(peak,equity)
        worst_dd=max(worst_dd,(peak-equity)/peak)
        observations.append({'close_ts':ts,'equity':equity,
            'realized_cash':realized,'unrealized_pnl':sum(p for _,p in marks),
            'reserved_margin':locked,'available_equity_proxy':equity-locked,
            'open_positions':len(opened)})
    return {'status':'RESEARCH_EXACT_CLOSE_ONLY_NOT_INTRABAR',
            'strategy':strategy,'partition':partition,'filter':filter_name or 'NONE',
            'initial_capital':initial_capital,'ending_realized_cash':final_cash,
            'realized_return':final_cash/initial_capital-1,
            'realized_event_drawdown':realized_dd,
            'close_observed_drawdown':worst_dd if observations else None,
            'complete_close_observations':len(observations),
            'skipped_incomplete_mark_timestamps':incomplete,
            'missing_position_marks':missing_position_marks,
            'missing_by_timeframe':dict(sorted(missing_by_frame.items())),
            'max_missing_positions_at_one_timestamp':max_missing_at_timestamp,
            'complete_timestamp_coverage':(len(observations)/(len(observations)+incomplete)
                if observations or incomplete else None),
            'accepted':len(accepted),'rejected_insufficient_margin':rejected,
            'excluded_by_filter':excluded,'unknown_filter':unknown,
            'censored_excluded':censored,'observations':observations,
            'risk_warnings':['NOT_INTRABAR_MAX_DRAWDOWN',
                'NOT_EXCHANGE_MARK_PRICE','NOT_LIQUIDATION_SIMULATION',
                'CENSORED_TRADES_EXCLUDED','MISSING_MARK_TIMESTAMPS_SKIPPED',
                'EXIT_FILL_TIMESTAMP_APPROXIMATED_AS_CANDLE_CLOSE']}

def main():
    folder=Path('research-output')
    cases=json.loads((folder/'bitget_reversal_candidates.json').read_text(encoding='utf-8'))['cases']
    histories={(c['symbol'],c['timeframe']):json.loads(
        (folder/('bitget_'+c['symbol']+'_'+c['timeframe']+'.json')).read_text(encoding='utf-8'))['candles']
        for c in cases}
    reports=[synchronized_marks(cases,histories,strategy=s,partition=p,filter_name=f)
             for s in ('early','confirmed') for p in ('TRAIN','HOLDOUT')
             for f in (None,'EMA20','EMA50','EMA200','higher')]
    (folder/'bitget_synchronized_equity_research.json').write_text(
        json.dumps({'research_only':True,'results':reports},indent=2),encoding='utf-8')
    print('synchronized research scenarios:',len(reports))

if __name__=='__main__':main()
