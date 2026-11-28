"""Research-only causal EMA alignment across completed higher timeframe candles.

Never reads an in-progress higher timeframe candle. Not a trade filter or
a claim of predictive benefit.
"""
from bisect import bisect_right
from badang_historical_integrity import FRAME_MS

ORDER=('15m','30m','1H','4H','1D')

def ema_at_closed_index(rows,index,period):
    if index<period-1:return None
    alpha=2/(period+1)
    ema=float(rows[0][4])
    for i in range(1,index+1):
        ema=alpha*float(rows[i][4])+(1-alpha)*ema
    return ema

def completed_higher_index(rows,frame,signal_close_ms):
    step=FRAME_MS[frame]
    # An OHLCV timestamp is the candle OPEN, so require open+step <= signal close.
    closes=[int(row[0])+step for row in rows]
    return bisect_right(closes,signal_close_ms)-1

def alignment(histories,symbol,frame,signal_bar,side):
    if side not in ('LONG','SHORT'):raise ValueError('invalid side')
    rows=histories[(symbol,frame)]
    if not (0<=signal_bar<len(rows)):raise ValueError('invalid signal bar')
    close_ms=int(rows[signal_bar][0])+FRAME_MS[frame]
    output={}
    for period in (20,50,200):
        ema=ema_at_closed_index(rows,signal_bar,period)
        output['EMA'+str(period)]=('INSUFFICIENT_HISTORY' if ema is None else
            'WITH' if ((float(rows[signal_bar][4])>=ema)==(side=='LONG')) else 'AGAINST')
    i=ORDER.index(frame)
    if i+1==len(ORDER):
        output['higher']='NO_HIGHER_FRAME'
    else:
        higher=ORDER[i+1]
        hrows=histories[(symbol,higher)]
        idx=completed_higher_index(hrows,higher,close_ms)
        ema=ema_at_closed_index(hrows,idx,20)
        output['higher']=('INSUFFICIENT_HISTORY' if ema is None else
            'WITH' if ((float(hrows[idx][4])>=ema)==(side=='LONG')) else 'AGAINST')
        output['higher_frame']=higher
        output['higher_last_closed_bar_index']=idx
        output['higher_last_close_ms']=(int(hrows[idx][0])+FRAME_MS[higher]) if idx>=0 else None
        if idx>=0 and output['higher_last_close_ms']>close_ms:
            raise AssertionError('higher candle is not closed at signal time')
    return output
