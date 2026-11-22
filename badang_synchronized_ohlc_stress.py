"""Stage 95: synchronized-close OHLC adverse portfolio stress (NOT realized MDD).

For each exact close timestamp, all active positions are stressed using the
high/low of candles ending at that SAME timestamp. This is a simultaneous
adverse-extremes scenario, NOT proof that extremes happened simultaneously.
"""
from badang_causal_mark_lookup import FRAME_MS

def stress_snapshots(snapshots,histories,initial_capital=10000.):
    candles={}
    for key,rows in histories.items():
        for row in rows:
            candles[(key,int(row[0])+FRAME_MS[key[1]])]=row
    peak=initial_capital
    max_dd=0.
    exact_count=0
    skipped=0
    worst=None
    for snap in snapshots:
        if snap["strict_observed_equity"] is None:
            skipped+=1
            continue
        adverse=0.
        missing=False
        for p in snap["active_positions"]:
            key=(p["symbol"],p["timeframe"])
            row=candles.get((key,snap["ts"]))
            if row is None:
                missing=True
                break
            high,low=float(row[2]),float(row[3])
            if not 0<low<=high:
                raise AssertionError("invalid stress OHLC")
            price=low if p["side"]=="LONG" else high
            direction=1 if p["side"]=="LONG" else -1
            adverse+=p["margin"]*p["leverage"]*direction*(price/p["entry_price"]-1)
        if missing:
            skipped+=1
            continue
        exact_count+=1
        equity=initial_capital+snap["realized_pnl"]+adverse
        peak=max(peak,equity)
        dd=max(0.,(peak-equity)/peak)
        if dd>max_dd:
            max_dd=dd
            worst={"ts":snap["ts"],"stress_equity":equity,
                   "stress_unrealized_pnl":adverse,"active_count":len(snap["active_positions"])}
    return {"status":"PASS" if exact_count else "NO_EXACT_SHARED_CLOSE",
            "exact_observations":exact_count,"skipped_observations":skipped,
            "synchronized_ohlc_stress_mdd":max_dd if exact_count else None,
            "worst_observation":worst,
            "warnings":["HYPOTHETICAL_SIMULTANEOUS_ADVERSE_EXTREMES",
                        "ONLY_EXACT_SHARED_CANDLE_CLOSE_TIMESTAMPS",
                        "NO_INTRABAR_ORDER_OR_MARK_PRICE",
                        "NOT_EXCHANGE_LIQUIDATION_OR_TRUE_INTRABAR_MDD"]}
