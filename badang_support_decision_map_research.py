"""Read-only support decision map; no orders, targets, or averaging down."""
from badang_support_timestamp_gate_544 import validated_support_reliability
from badang_support_zones_541 import _candle


def support_decision_map(candles, symbol, timeframe, mode="scalp", *, confirmed=True, exchange_now_ms=None):
    """Describe ordered support observation zones and invalidation conditions.

    No implied rebound probability. Input timestamp continuity must be verified
    upstream, as the support research module only validates OHLCV values.
    """
    if not confirmed:
        return {"status": "unconfirmed", "observation_zones": [], "trading_ready": False}
    if exchange_now_ms is None:
        return {"status": "missing_exchange_clock", "observation_zones": [], "trading_ready": False}
    result = validated_support_reliability(candles, symbol, timeframe, mode,
                                           exchange_now_ms=exchange_now_ms)
    if result["status"] != "ok":
        return {"status": result["status"], "observation_zones": [],
                "trading_ready": False}
    close = _candle(candles[-1])["close"]
    # Rank by proximity, not evidence score: next support means next in price.
    zones = sorted((z for z in result["zones"]
                    if z["upper"] < close and z["status"] != "broken"),
                   key=lambda z: z["upper"], reverse=True)
    observations = []
    for index, zone in enumerate(zones):
        observations.append({
            "order": index + 1,
            "zone_lower": zone["lower"],
            "zone_upper": zone["upper"],
            "evidence_grade": zone["evidence_grade"],
            "evidence_score_not_probability": zone["evidence_score"],
            "estimated_volume_confluence": zone["volume_node"],
            "watch_for": "Confirmed price reaction, volume and momentum divergence",
            "invalidated_if": zone["invalidated_if"],
            "next_observation_zone": None,
            "action": "Observe and reassess; no automatic buy or order",
        })
    for i in range(len(observations)-1):
        observations[i]["next_observation_zone"] = {
            "lower": observations[i+1]["zone_lower"],
            "upper": observations[i+1]["zone_upper"],
        }
    return {"status": "ok", "reference_close": close,
            "observation_zones": observations,
            "rebound_probability": None, "trading_ready": False,
            "warnings": result["warnings"] + [
                "Zone ordering is price-based, not an instruction to average down",
                "Volume profile is OHLCV-estimated, not actual order-book depth",
                "Trend, Elliott wave and divergence need separate confirmation",
            ]}
