"""Shared chronological margin allocation for offline research; no orders.

Exit at a candle's recorded exit bar is treated as end-of-bar. Entries
at the same timestamp do not reuse proceeds from that exit.
"""
def allocate(events,initial_capital,margin_fraction,leverage,max_total_margin_fraction):
    events=sorted(events,key=lambda a:(a['entry_ts'],a['exit_ts'],a['key']))
    active=[];accepted=[];rejected=0;cash=initial_capital
    for e in events:
        start=e['entry_ts']
        still=[]
        for a in active:
            if a['exit_ts']<start:
                cash+=a['pnl']
            else:
                still.append(a)
        active=still
        locked=sum(a['margin'] for a in active)
        margin=min(max(0,cash)*margin_fraction,
                   max(0,cash)*max_total_margin_fraction-locked,
                   max(0,cash-locked))
        if margin<=0:
            rejected+=1
            continue
        t=e['t']
        a=dict(e,margin=margin,exposure=margin*leverage,
               pnl=margin*leverage*float(t['net_return']))
        active.append(a);accepted.append(a)
    return accepted,rejected

def realized_path(accepted,initial_capital):
    capital=initial_capital;peak=capital;dd=0.
    for a in sorted(accepted,key=lambda a:(a['exit_ts'],a['entry_ts'])):
        capital+=a['pnl']
        peak=max(peak,capital)
        dd=max(dd,(peak-capital)/peak)
    return capital,dd
