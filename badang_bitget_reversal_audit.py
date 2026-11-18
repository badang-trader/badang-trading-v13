"""Read-only primary Bitget reversal candidate audit; no trading orders."""
import json
from collections import Counter
from pathlib import Path
from badang_reversal_research import reversal_candidates
from badang_reversal_divergence import confirmed_divergences
from badang_reversal_outcomes import evaluate_reversal_candidates
from badang_reversal_backtest import replay
from badang_historical_integrity import audit_historical_candles

def main():
    folder=Path('research-output')
    manifest=json.loads((folder/'bitget_manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='COMPLETE':
        raise ValueError('primary Bitget history incomplete')
    cases=[]
    for symbol in ('BTC','ETH'):
        for frame in ('15m','30m','1H','4H','1D'):
            payload=json.loads((folder/f'bitget_{symbol}_{frame}.json').read_text(encoding='utf-8'))
            rows=payload['candles']
            audit_historical_candles(rows,frame,asof_ms=manifest['collected_at_ms'])
            candidates=reversal_candidates(rows)
            divergences=confirmed_divergences(rows)
            outcomes=evaluate_reversal_candidates(rows,candidates,horizon=24)
            early_replay=replay(rows,'EARLY')
            confirmed_replay=replay(rows,'CONFIRMED')
            divergence_types=Counter(d['classification'] for d in divergences)
            divergence_indicators=Counter(d['indicator'] for d in divergences)
            candidate_directions=Counter(d['direction'] for d in candidates)
            # Association requires divergence availability at or before the
            # candidate and within 24 setup bars; no future divergence matching.
            associated=0
            for candidate in candidates:
                direction='BULLISH' if candidate['direction']=='BULLISH' else 'BEARISH'
                at=candidate['available_at_bar']
                if any(d['classification'].startswith('REGULAR_'+direction)
                       and at-24<=d['available_at_bar']<=at for d in divergences):
                    associated+=1
            cases.append({'symbol':symbol,'timeframe':frame,'closed_bars':len(rows),
                'candidate_count':len(candidates),
                'confirmed_structure_break_count':sum(x['confirmed_at_bar'] is not None for x in candidates),
                'candidates':candidates,'divergence_count':len(divergences),
                'divergences':divergences,'outcomes':outcomes,
                'reversal_backtest':{'early':early_replay,'confirmed':confirmed_replay},
                'divergence_by_type':dict(divergence_types),
                'divergence_by_indicator':dict(divergence_indicators),
                'candidates_by_direction':dict(candidate_directions),
                'candidates_with_prior_regular_divergence':associated,
                'first_closed_bar_timestamp_ms':rows[0][0],
                'last_closed_bar_timestamp_ms':rows[-1][0],
                'observation_split_bar':int(len(rows)*0.7),
                'train_candidate_count':sum(x['available_at_bar']<int(len(rows)*0.7) for x in candidates),
                'holdout_candidate_count':sum(x['available_at_bar']>=int(len(rows)*0.7) for x in candidates)})
    output={'status':'CAUSAL_REVERSAL_CANDIDATES_ONLY',
        'primary_exchange':'BITGET','elliott_classification':'NOT_VALIDATED',
        'rsi_macd_divergence':'CAUSAL_CONFIRMED_PIVOTS','historical_flow':'NOT_AVAILABLE',
        'profitability':'RESEARCH_ONLY_FIXED_RULES','reversal_success_rate':'NOT_ESTABLISHED',
        'limitations':['A pivot is known only after right-side bars close',
            'Structure break is not proof of lasting reversal',
            'Divergence does not prove a lasting reversal; Elliott not classified'],
        'cases':cases}
    (folder/'bitget_reversal_candidates.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':output['status'],'markets':len(cases),
        'total_candidates':sum(x['candidate_count'] for x in cases),
        'confirmed_structure_breaks':sum(x['confirmed_structure_break_count'] for x in cases),
        'divergences':sum(x['divergence_count'] for x in cases),
        'outcomes':{status:sum(x['outcomes']['counts'].get(status,0) for x in cases)
                    for status in ('INVALIDATED','STRUCTURE_LEVEL_TOUCHED','AMBIGUOUS_SAME_BAR','UNRESOLVED','CENSORED_END_OF_DATA')}}))

if __name__=='__main__':main()
