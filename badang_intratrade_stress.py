"""Conservative OHLC stress audit for a *single* research position.

Not a liquidation engine or executable fill simulator. Uses each candle's
adverse extreme, so intra-candle sequence and liquidation timing are unknown.
"""
def adverse_excursion(candles, entry_bar, exit_bar, entry_price, side, leverage=1.0,
                      margin=1.0, assumed_maintenance_rate=None):
    if side not in ('LONG','SHORT') or entry_price<=0 or leverage<=0 or margin<=0:
        raise ValueError('invalid position')
    if not 0<=entry_bar<=exit_bar<len(candles):
        raise ValueError('invalid interval')
    if assumed_maintenance_rate is not None and not 0<=assumed_maintenance_rate<1:
        raise ValueError('invalid maintenance rate')
    exposure=margin*leverage
    worst=0.0
    observations=[]
    for i in range(entry_bar,exit_bar+1):
        candle=candles[i]
        low=float(candle[3]);high=float(candle[2])
        if low<=0 or high<low:
            raise ValueError('invalid candle')
        adverse=(low/entry_price-1) if side=='LONG' else (1-high/entry_price)
        pnl=exposure*adverse
        worst=min(worst,pnl)
        observations.append({'bar':i,'adverse_unrealized_pnl':pnl})
    # This is an indicative threshold crossing only. It excludes funding,
    # liquidation fees, mark price, risk tiers, cross-margin and other positions.
    breach=None
    if assumed_maintenance_rate is not None:
        threshold=-(margin-exposure*assumed_maintenance_rate)
        breach=any(x['adverse_unrealized_pnl']<=threshold for x in observations)
    return {'research_only':True,'worst_intrabar_unrealized_pnl':worst,
            'worst_intrabar_loss_on_margin':-worst/margin,
            'assumed_maintenance_rate':assumed_maintenance_rate,
            'hypothetical_threshold_crossed':breach,
            'actual_liquidation_verified':False,
            'intrabar_order_unknown':True,
            'mark_price_not_available':True,
            'funding_and_liquidation_fees_not_modeled':True,
            'cross_margin_and_other_positions_not_modeled':True}

def stress_summary(cases,histories,*,strategy='early',partition='HOLDOUT',
                   leverage=2.0,margin=500.0):
    total=0;worst=0.;censored=0
    for case in cases:
        key=(case['symbol'],case['timeframe'])
        for t in case['reversal_backtest'][strategy]['trades']:
            if t['partition']!=partition:continue
            if t['net_return'] is None:
                censored+=1;continue
            rows=histories[key]
            i=t['entry_bar'];j=t['exit_bar']
            entry=float(rows[i][1])
            a=adverse_excursion(rows,i,j,entry,t['side'],leverage,margin)
            total+=1;worst=min(worst,a['worst_intrabar_unrealized_pnl'])
    return {'completed_trades_audited':total,'censored_not_audited':censored,
            'worst_single_position_intrabar_pnl':worst,
            'portfolio_concurrent_intrabar_drawdown':'NOT_CALCULATED',
            'actual_liquidation':'NOT_VERIFIED','research_only':True}
