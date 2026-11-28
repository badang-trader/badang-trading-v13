"""Research-only chronological holdout separation; no claim of trained model."""
def partition_completed_trades(trades, split_index, total_bars):
    if not isinstance(total_bars,int) or isinstance(total_bars,bool) or total_bars<2:
        raise ValueError("Invalid historical length")
    if not isinstance(split_index,int) or isinstance(split_index,bool) or not 1<=split_index<total_bars:
        raise ValueError("Invalid holdout boundary")
    before=[]
    holdout=[]
    last_exit=-1
    for trade in trades:
        if not isinstance(trade,dict):
            raise ValueError("Invalid completed trade")
        signal=trade.get("signal_index")
        entry=trade.get("entry_index")
        exit_index=trade.get("exit_index")
        if any(not isinstance(v,int) or isinstance(v,bool) for v in (signal,entry,exit_index)):
            raise ValueError("Invalid trade indices")
        if not (last_exit<signal<entry<=exit_index<total_bars):
            raise ValueError("Invalid trade chronology")
        last_exit=exit_index
        if exit_index<split_index:
            before.append(trade)
        elif signal>=split_index:
            holdout.append(trade)
        # Discard boundary-straddling trades rather than leaking outcomes.
    return {"development":before,"holdout":holdout,
            "boundary_excluded":len(trades)-len(before)-len(holdout),
            "split_index":split_index,"total_bars":total_bars}
