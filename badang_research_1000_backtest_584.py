"""Read-only 1000-confirmed-bar Bitget research; no orders or deployment."""
import json
from pathlib import Path
from badang_research_history_582 import research_history
from badang_live_historical_research_551 import (
    convert_closed_candles, FRAME_INTERVAL_MS, validate_research_timestamps)
from badang_engine_research_549 import research_engine_backtest
from badang_research_sample_554 import assess_sample
from badang_research_holdout_metrics_578 import holdout_performance

TARGETS = (("BTCUSDT", "15m", "scalp"), ("ETHUSDT", "15m", "scalp"),
           ("BTCUSDT", "1H", "scalp"), ("ETHUSDT", "1H", "scalp"))

def evaluate_target(symbol, frame, mode, *, fetch=None, engine=None):
    kwargs = {"target_bars": 1000, "max_pages": 6}
    if fetch is not None:
        kwargs["fetch"] = fetch
    history = research_history(symbol, frame, **kwargs)
    if history["status"] != "ok":
        return {"symbol": symbol, "frame": frame, "mode": mode,
                "status": "insufficient_history",
                "confirmed_bars": history.get("confirmed_bars", 0),
                "stop_reason": history.get("stop_reason"),
                "trading_ready": False}
    # The history adapter already excluded open bars. The converter normally
    # removes the newest row, so append a sentinel only for this conversion.
    rows = history["candles"]
    snapshot = {"candles": rows + [rows[-1]]}
    closed = convert_closed_candles(snapshot)
    validate_research_timestamps(closed, FRAME_INTERVAL_MS[frame])
    if len(closed) != 1000:
        raise ValueError("Research sample is not exactly 1000 confirmed bars")
    backtest = engine if engine is not None else research_engine_backtest
    result = backtest(closed, mode=mode, horizon=3,
                      fee_per_side=0.0006, slippage_per_side=0.0005)
    trades = result["trades"]
    sample = assess_sample(len(trades), len(closed))
    return {"symbol": symbol, "frame": frame, "mode": mode,
            "status": "evaluated", "confirmed_bars": len(closed),
            "completed_trades": len(trades),
            "sample_assessment": sample,
            "chronological_holdout": holdout_performance(
                trades, int(len(closed) * 0.7), len(closed)),
            "summary": result["summary"],
            "fee_per_side_assumed": 0.0006,
            "slippage_per_side_assumed": 0.0005,
            "trading_ready": False}

def main():
    results = []
    for symbol, frame, mode in TARGETS:
        try:
            results.append(evaluate_target(symbol, frame, mode))
        except Exception as exc:
            results.append({"symbol": symbol, "frame": frame, "mode": mode,
                            "status": "error", "error_type": type(exc).__name__,
                            "error_message": str(exc)[:200],
                            "trading_ready": False})
    report = {"read_only": True, "trading_ready": False, "results": results}
    Path("badang-research-1000-backtest.json").write_text(
        json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8")
    print("BADANG_1000_BACKTEST " + json.dumps(
        [{"symbol": x["symbol"], "frame": x["frame"], "status": x["status"],
          "completed_trades": x.get("completed_trades")} for x in results]))
    if any(x["status"] != "evaluated" for x in results):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
