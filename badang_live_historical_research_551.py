"""Bounded live public Bitget historical research check; no orders.

Only the exchange's confirmed candles are used. Reports results without
asserting profitability. Live API failures fail this validation step.
"""
import json
import math
import re
from bitget_market_data import fastest_candles
from badang_engine_research_549 import research_engine_backtest
from badang_research_sample_554 import assess_sample
from badang_research_regime_metrics_556 import summarize_by_regime
from badang_research_cost_sensitivity_560 import cost_sensitivity
from badang_research_regime_sample_563 import regime_sample_review
from badang_research_regime_exposure_564 import regime_exposure
from badang_research_timestamp_validation_569 import validate_research_timestamps
from badang_research_holdout_metrics_578 import holdout_performance
from badang_support_holdout_550 import chronological_support_holdout

def parse_exchange_timestamp(value):
    """Require exchange epoch milliseconds, never silently coerce seconds."""
    if isinstance(value,bool) or not (
        isinstance(value,int) or (isinstance(value,str) and re.fullmatch(r"[0-9]{13}",value))
    ):
        raise ValueError("Invalid exchange millisecond timestamp")
    timestamp=int(value)
    if not 10**12<=timestamp<10**14:
        raise ValueError("Exchange timestamp must be epoch milliseconds")
    return timestamp

def _exchange_number(value,field,allow_zero=False):
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):
        raise ValueError("Invalid exchange "+field)
    if isinstance(value,str) and not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)",value):
        raise ValueError("Invalid exchange "+field)
    number=float(value)
    if not math.isfinite(number) or number<0 or (number==0 and not allow_zero):
        raise ValueError("Invalid exchange "+field)
    return number

def convert_closed_candles(snapshot):
    """Validate and convert confirmed Bitget rows; exclude newest open bar."""
    if not isinstance(snapshot,dict) or not isinstance(snapshot.get("candles"),list):
        raise ValueError("Invalid exchange candle snapshot")
    if len(snapshot["candles"])<2:
        raise ValueError("Insufficient exchange candles to confirm a closed bar")
    rows=[]
    for row in snapshot["candles"][:-1]:
        if not isinstance(row,(list,tuple)) or len(row)<6:
            raise ValueError("Invalid exchange OHLCV row")
        op=_exchange_number(row[1],"open")
        hi=_exchange_number(row[2],"high")
        lo=_exchange_number(row[3],"low")
        cl=_exchange_number(row[4],"close")
        vol=_exchange_number(row[5],"volume",allow_zero=True)
        if hi<max(op,lo,cl) or lo>min(op,hi,cl):
            raise ValueError("Inconsistent exchange OHLC")
        rows.append({"timestamp":parse_exchange_timestamp(row[0]),
                     "open":op,"high":hi,"low":lo,"close":cl,"volume":vol})
    return rows

TARGETS = tuple(
    (symbol, frame, mode)
    for symbol in ("BTCUSDT", "ETHUSDT")
    for frame, mode in (("15m", "scalp"), ("30m", "scalp"),
                        ("1H", "scalp"), ("1H", "swing"),
                        ("4H", "swing"), ("1D", "swing"))
)
FRAME_INTERVAL_MS = {"15m": 900000, "30m": 1800000, "1H": 3600000,
                     "4H": 14400000, "1D": 86400000}

def main():
    reports=[]
    for symbol,frame,mode in TARGETS:
        snapshot=fastest_candles(symbol,frame)
        closed=convert_closed_candles(snapshot)
        validate_research_timestamps(closed,FRAME_INTERVAL_MS[frame])
        if len(closed)<210:
            raise ValueError("Too few confirmed historical bars: "+symbol+" "+frame)
        result=research_engine_backtest(closed,mode=mode,horizon=3)
        support_research=None
        if (symbol,frame,mode) in (("BTCUSDT","15m","scalp"),("BTCUSDT","30m","scalp"),("BTCUSDT","1H","scalp"),("BTCUSDT","4H","swing"),("ETHUSDT","15m","scalp"),("ETHUSDT","30m","scalp"),("ETHUSDT","1H","scalp"),("ETHUSDT","4H","swing")):
            support_frame={"15m":"15m","30m":"30m","1H":"1h","4H":"4h"}[frame]
            support_research=chronological_support_holdout(
                closed,symbol.removesuffix("USDT"),support_frame,mode,
                exchange_now_ms=closed[-1]["timestamp"]+FRAME_INTERVAL_MS[frame],
                horizon=8,warmup=90,rebound_pct=0.5,min_resolved=30)
        if support_research is not None and support_research.get("status") == "ok":
            for partition in ("train", "holdout"):
                section = support_research[partition]
                grade_total = sum(group["events"] for group in
                                  section["by_evidence_grade"].values())
                if grade_total != section["event_count"]:
                    raise ValueError("Support grade event accounting mismatch: "+
                                     symbol+" "+frame+" "+partition)
                regime_groups = section.get("by_pre_touch_regime", {})
                if sum(group["events"] for group in regime_groups.values()) != section["event_count"]:
                    raise ValueError("Support regime event accounting mismatch: "+
                                     symbol+" "+frame+" "+partition)
                if sum(group["resolved"] for group in regime_groups.values()) != section["resolved_count"]:
                    raise ValueError("Support regime resolved accounting mismatch: "+
                                     symbol+" "+frame+" "+partition)
                grade_resolved = sum(group["resolved"] for group in
                                     section["by_evidence_grade"].values())
                if grade_resolved != section["resolved_count"]:
                    raise ValueError("Support grade resolved accounting mismatch: "+
                                     symbol+" "+frame+" "+partition)
        metrics=result["summary"]
        reports.append({"symbol":symbol,"frame":frame,"mode":mode,
                        "confirmed_bars":len(closed),
                        "support_holdout_research":support_research,
                        "mode_specific_strategy_verified":False,
                        "mode_comparison_warning":"SCALP_SWING_SHARE_SIGNAL_RULES_AND_HORIZON",
                        "research_window_start_ms":closed[0]["timestamp"],
                        "research_window_end_ms":closed[-1]["timestamp"],
                        "trades":len(result["trades"]),
                        "skipped_overlaps":result["skipped_overlaps"],
                        "chronological_holdout":holdout_performance(result["trades"],int(len(closed)*0.7),len(closed)),
                        "conditional_regime_metrics":summarize_by_regime(closed,result["trades"]),
                        "regime_sample_review":regime_sample_review(closed,result["trades"]),
                        "regime_exposure":regime_exposure(closed),
                        "execution_cost_sensitivity":cost_sensitivity(result["trades"]),
                        "sample_assessment":assess_sample(len(result["trades"]),len(closed)),
                        "win_rate":metrics["win_rate"] if metrics else None,
                        "compounded_net_return":metrics["compounded_net_return"] if metrics else None,
                        "max_drawdown":metrics["max_drawdown"] if metrics else None,
                        "fee_per_side_assumed":0.0006,
                        "slippage_per_side_assumed":0.0005})
    insufficient = [r for r in reports if not r["sample_assessment"]["sample_adequate_for_preliminary_review"]]
    report={"read_only":True,"trading_enabled":False,
            "historical_sample_coverage":{
                "target_count":len(reports),
                "insufficient_target_count":len(insufficient),
                "all_targets_preliminary_sample_adequate":not insufficient,
                "minimum_bars_required":1000,
                "minimum_completed_trades_required":30,
                "warnings":["Insufficient history or completed trades in one or more timeframes"]
                           if insufficient else []},
            "results":reports}
    encoded=json.dumps(report,allow_nan=False)
    from pathlib import Path
    Path("badang-live-historical-research.json").write_text(encoded+"\n",encoding="utf-8")
    print("LIVE_HISTORICAL_RESEARCH_SUMMARY "+encoded)
if __name__=="__main__":
    main()
