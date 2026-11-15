"""Read-only Bitget confirmed-candle Elliott scenario observation research."""
import json
from pathlib import Path
from badang_research_history_582 import research_history
from badang_live_historical_research_551 import (
    convert_closed_candles, FRAME_INTERVAL_MS, validate_research_timestamps)
from badang_wave_causal_replay_588 import replay_wave_scenarios

TARGETS = (("BTCUSDT", "15m"), ("ETHUSDT", "15m"),
           ("BTCUSDT", "1H"), ("ETHUSDT", "1H"))

def evaluate_wave_target(symbol, frame, *, fetch=None, replay=None):
    kwargs = {"target_bars": 1000, "max_pages": 6}
    if fetch is not None:
        kwargs["fetch"] = fetch
    history = research_history(symbol, frame, **kwargs)
    if history["status"] != "ok":
        return {"symbol": symbol, "frame": frame,
                "status": "insufficient_history",
                "stop_reason": history.get("stop_reason"),
                "trading_ready": False}
    raw = history["candles"]
    closed = convert_closed_candles({"candles": raw + [raw[-1]]})
    validate_research_timestamps(closed, FRAME_INTERVAL_MS[frame])
    if len(closed) != 1000:
        raise ValueError("Expected exactly 1000 confirmed bars")
    engine = replay or replay_wave_scenarios
    replay_result = engine(closed, warmup=205, stride=5)
    observations = replay_result["observations"]
    if not observations:
        raise ValueError("Empty causal wave replay")
    by_direction = {"up": 0, "down": 0}
    patterns = {}
    invalidated = 0
    for observation in observations:
        for candidate in observation["scenarios"]:
            direction = candidate["direction"]
            if direction not in by_direction:
                raise ValueError("Invalid wave candidate direction")
            by_direction[direction] += 1
            pattern = candidate["pattern"]
            patterns[pattern] = patterns.get(pattern, 0) + 1
            invalidated += candidate["invalidation_status"] == "crossed_or_at_level"
    return {"symbol": symbol, "frame": frame, "status": "evaluated",
            "confirmed_bars": len(closed),
            "observations": len(observations),
            "observations_with_candidates": sum(
                bool(o["candidate_count"]) for o in observations),
            "candidate_observation_counts_by_direction": by_direction,
            "candidate_observation_counts_by_pattern": patterns,
            "already_crossed_invalidation_observations": invalidated,
            "counts_are_repeated_observations_not_independent_trades": True,
            "prediction_accuracy_verified": False,
            "profitability_verified": False,
            "trading_ready": False}

def main():
    results = []
    for symbol, frame in TARGETS:
        try:
            results.append(evaluate_wave_target(symbol, frame))
        except Exception as exc:
            results.append({"symbol": symbol, "frame": frame,
                            "status": "error", "error_type": type(exc).__name__,
                            "error_message": str(exc)[:200],
                            "trading_ready": False})
    report = {"read_only": True, "trading_ready": False, "results": results}
    Path("badang-wave-live-research.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    print("BADANG_WAVE_RESEARCH " + json.dumps(
        [{"symbol": r["symbol"], "frame": r["frame"], "status": r["status"]}
         for r in results]))
    if any(r["status"] != "evaluated" for r in results):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
