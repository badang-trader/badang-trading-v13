"""Research-only Bitget technical experiment; NOT the BADANG trading score.

Signals use only closed Bitget candles and the existing indicator adapter.
No historical OI/CVD/trade-side observations are asserted. The independent
holdout is the last 30% of setup candles, with no parameter tuning.
"""
import json
from pathlib import Path
from badang_historical_integrity import FRAME_MS,audit_historical_candles
from badang_historical_signal_adapter import analyze_closed_prefix
from badang_walkforward_audit import audit_trades

MODES={'scalp':('15m','30m','1H'),'swing':('1H','4H','1D')}

def closed_prefix(rows,frame,asof):
    return [r for r in rows if int(r[0])+FRAME_MS[frame]<=asof]

def technical_only_signal(setup,lower,higher,mode):
    a=analyze_closed_prefix(setup)
    b=analyze_closed_prefix(lower)
    c=analyze_closed_prefix(higher)
    if not all((a,b,c)):return None
    if a['trend'] not in ('UP','DOWN') or c['trend']!=a['trend']:
        return None
    side='LONG' if a['trend']=='UP' else 'SHORT'
    opposite='bearish' if side=='LONG' else 'bullish'
    if a['fake_breakout'] or a['divergence']==opposite or b['divergence']==opposite:
        return None
    # Independent research-only 100-point rubric; NOT the original BADANG score.
    score=40 # setup/higher trend alignment
    score+=20 if (a['rsi']>=50 if side=='LONG' else a['rsi']<=50) else 0
    score+=20 if (a['macd']>=a['macd_signal'] if side=='LONG' else a['macd']<=a['macd_signal']) else 0
    score+=10 if a['volume_ratio']>=1.2 else 0
    score+=10 if b['divergence']==('bullish' if side=='LONG' else 'bearish') else 0
    if score<80:return None
    entry=a['price']
    atr=a['atr']
    if atr<=0:return None
    # ATR-only research stops/targets, not production scenario().
    stop=entry-1.5*atr if side=='LONG' else entry+1.5*atr
    target=entry+3*atr if side=='LONG' else entry-3*atr
    if min(stop,target)<=0:return None
    return {'side':side,'score':score,'stop':stop,'target':target,'mode':mode}

def run_experiment(frames,mode):
    lower,setup,higher=MODES[mode]
    candles=frames[setup]
    split=int(len(candles)*0.7)
    signals=[]
    rejected_history=0
    for bar in range(204,len(candles)-1):
        asof=int(candles[bar][0])+FRAME_MS[setup]
        prefixes={f:closed_prefix(frames[f],f,asof) for f in (lower,setup,higher)}
        if any(len(prefixes[f])<205 for f in (lower,setup,higher)):
            rejected_history+=1
            continue
        s=technical_only_signal(prefixes[setup],prefixes[lower],prefixes[higher],mode)
        if s:
            signals.append({'bar':bar,'known_at_bar':bar,
                'signal_timestamp':candles[bar][0],**s})
    # Partition by signal date. Trade outcomes can extend across boundary,
    # so evaluate train and holdout on their own candle slices.
    def partition(start,end):
        selected=[]
        for s in signals:
            if start<=s['bar']<end-1:
                item=dict(s)
                item['bar']-=start
                item['known_at_bar']-=start
                selected.append(item)
        result=audit_trades(candles[start:end],selected)
        return {'signals':len(selected),'trades':len(result['trades']),
                'groups':result['groups'],'assumptions':result['assumptions']}
    return {'setup_bars':len(candles),'split_bar':split,
            'rejected_insufficient_history':rejected_history,
            'train':partition(0,split),'holdout':partition(split,len(candles))}

def main():
    folder=Path('research-output')
    manifest=json.loads((folder/'bitget_manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='COMPLETE':raise ValueError('Bitget data incomplete')
    output={'status':'TECHNICAL_ONLY_RESEARCH_NOT_BADANG',
        'primary_exchange':'BITGET','secondary_exchange':'NOT_USED_FOR_SIGNALS',
        'historical_flow':'NOT_AVAILABLE','original_badang_score':'NOT_EVALUATED',
        'score_rubric':'40 trend alignment + 20 RSI + 20 MACD + 10 volume + 10 lower divergence',
        'execution':'next bar open, 0.06% fee and 0.03% slippage each side',
        'limitations':['no OI','no trade CVD','no original BADANG score',
            'short history','no parameter tuning','holdout sample may be small'],
        'results':[]}
    for symbol in ('BTC','ETH'):
        frames={}
        for frame in ('15m','30m','1H','4H','1D'):
            payload=json.loads((folder/f'bitget_{symbol}_{frame}.json').read_text(encoding='utf-8'))
            audit_historical_candles(payload['candles'],frame,asof_ms=manifest['collected_at_ms'])
            frames[frame]=payload['candles']
        for mode in MODES:
            output['results'].append({'symbol':symbol,'mode':mode,
                **run_experiment(frames,mode)})
    (folder/'bitget_technical_only_experiment.json').write_text(
        json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(output,ensure_ascii=False))

if __name__=='__main__':main()
