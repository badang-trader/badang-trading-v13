"""Read-only primary Bitget reversal candidate audit; no trading orders."""
import json
from pathlib import Path
from badang_reversal_research import reversal_candidates
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
            cases.append({'symbol':symbol,'timeframe':frame,'closed_bars':len(rows),
                'candidate_count':len(candidates),
                'confirmed_structure_break_count':sum(x['confirmed_at_bar'] is not None for x in candidates),
                'candidates':candidates})
    output={'status':'CAUSAL_REVERSAL_CANDIDATES_ONLY',
        'primary_exchange':'BITGET','elliott_classification':'NOT_VALIDATED',
        'rsi_macd_divergence':'NOT_EVALUATED','historical_flow':'NOT_AVAILABLE',
        'profitability':'NOT_EVALUATED',
        'limitations':['A pivot is known only after right-side bars close',
            'Structure break is not proof of lasting reversal',
            'No Elliott counts or RSI/MACD divergence are asserted'],
        'cases':cases}
    (folder/'bitget_reversal_candidates.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':output['status'],'markets':len(cases),
        'total_candidates':sum(x['candidate_count'] for x in cases),
        'confirmed_structure_breaks':sum(x['confirmed_structure_break_count'] for x in cases)}))

if __name__=='__main__':main()
