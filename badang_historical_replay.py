"""Research-only chronological replay of BADANG signals.

The caller supplies real historical closed OHLCV and a signal_fn that uses ONLY
the passed prefix. A signal must provide actual BADANG score/side/stop/target;
this module never invents scores or retroactively reuses today's scan.
"""
from badang_historical_integrity import audit_historical_candles, FRAME_MS
from badang_walkforward_audit import audit_trades

def replay_historical_signals(rows, timeframe, *, asof_ms, signal_fn,
                              warmup_bars=205, mode='UNSPECIFIED',
                              fee_rate=.0006, slippage_rate=.0003):
    integrity=audit_historical_candles(rows,timeframe,asof_ms=asof_ms)
    if not callable(signal_fn): raise ValueError('signal_fn required')
    if not isinstance(warmup_bars,int) or isinstance(warmup_bars,bool) or warmup_bars<2:
        raise ValueError('invalid warmup')
    signals=[]
    # The last bar cannot be entered at next open. Every call gets a detached
    # copy of the prefix so no later bars can be inspected or mutated.
    for bar in range(warmup_bars-1,len(rows)-1):
        prefix=tuple(tuple(row) for row in rows[:bar+1])
        s=signal_fn(prefix,timeframe)
        if s is None: continue
        if not isinstance(s,dict): raise ValueError('signal must be a dict')
        # Do not permit callbacks to override provenance or timing.
        if s.get('side') not in ('LONG','SHORT'): continue
        signals.append({'bar':bar,'known_at_bar':bar,
                        'signal_timestamp':rows[bar][0],
                        'side':s['side'],'score':s['score'],
                        'stop':s['stop'],'target':s['target'],'mode':mode})
    result=audit_trades(rows,signals,fee_rate=fee_rate,slippage_rate=slippage_rate)
    return {'integrity':integrity,'generated_signals':len(signals),
            'backtest':result,'data_provenance':'CALLER_SUPPLIED_NOT_VERIFIED',
            'signal_provenance':'CALLBACK_REPLAY_NOT_INDEPENDENTLY_AUDITED',
            'historical_market_performance_verified':False}
