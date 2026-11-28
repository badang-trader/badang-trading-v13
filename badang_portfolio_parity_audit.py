"""Fail closed when the two offline portfolio reports disagree.

Reads only generated research artifacts. Does not place orders or access exchanges.
"""
import json
from pathlib import Path

FIELDS=(('accepted','accepted'),('rejected_insufficient_margin','rejected_insufficient_margin'),
        ('ending_capital','ending_realized_cash'),
        ('realized_return','realized_return'),
        ('realized_event_drawdown','realized_event_drawdown'))

def verify(realized,synchronized,tolerance=1e-9):
    a=realized['results'];b=synchronized['results']
    if len(a)!=len(b):raise ValueError('scenario count mismatch')
    lookup={}
    for x in b:
        key=(x['strategy'],x['partition'],x['filter'])
        if key in lookup:raise ValueError('duplicate synchronized scenario')
        lookup[key]=x
    if len(lookup)!=len(b):raise ValueError('duplicate synchronized scenario')
    for x in a:
        key=(x['strategy'],x['partition'],x['filter'])
        if key not in lookup:raise ValueError('missing scenario '+str(key))
        y=lookup.pop(key)
        for p,q in FIELDS:
            if abs(x[p]-y[q])>tolerance:
                raise ValueError('portfolio parity mismatch '+str((key,p,x[p],y[q])))
    if lookup:raise ValueError('extra synchronized scenarios')
    return {'status':'PASS','scenarios':len(a),'fields_checked':len(FIELDS),
            'not_independent_data':True,'liquidation_verified':False}

def main():
    folder=Path('research-output')
    a=json.loads((folder/'bitget_portfolio_research.json').read_text(encoding='utf-8'))
    b=json.loads((folder/'bitget_synchronized_equity_research.json').read_text(encoding='utf-8'))
    result=verify(a,b)
    (folder/'bitget_portfolio_parity_audit.json').write_text(
        json.dumps(result,indent=2),encoding='utf-8')
    print('portfolio parity:',result)

if __name__=='__main__':main()
