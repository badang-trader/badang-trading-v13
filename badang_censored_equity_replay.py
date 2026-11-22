"""Research-only chronological equity replay including censored positions.

Prices are observed closed-candle prices, NOT exchange mark prices. No orders,
synthetic exits, forward interpolation, or liquidation predictions.
"""
from badang_causal_mark_lookup import observed_mark

def replay(events, histories, observation_times, *, initial_capital=10000.0,
           margin_fraction=.05, max_margin_fraction=.30, max_age_ms=0,
           include_active_positions=False):
    if initial_capital <= 0 or not 0 < margin_fraction <= 1 or not 0 < max_margin_fraction <= 1:
        raise ValueError("invalid capital or margin settings")
    if max_age_ms < 0:
        raise ValueError("invalid age")
    timeline = {}
    for event in events:
        if event["entry_ts"] > event.get("exit_ts", float("inf")):
            raise ValueError("exit before entry")
        if event["entry_price"] <= 0 or event["leverage"] <= 0:
            raise ValueError("invalid price/leverage")
        if event["reason"] not in ("CLOSED", "END_OF_DATA", "END_OF_PARTITION"):
            raise ValueError("invalid reason")
        if event["reason"] == "CLOSED" and ("exit_ts" not in event or "net_return" not in event):
            raise ValueError("completed trade missing exit")
        if event["reason"] == "END_OF_PARTITION":
            boundary = event.get("partition_end_ts")
            if boundary is None or boundary < event["entry_ts"]:
                raise ValueError("partition boundary required")
            timeline.setdefault(boundary, []).append(("partition_end", event))
        timeline.setdefault(event["entry_ts"], []).append(("entry", event))
        if event["reason"] == "CLOSED":
            timeline.setdefault(event["exit_ts"], []).append(("exit", event))
    active = {}
    realized = 0.0
    expired_partition_ids = []
    rejected = []
    snapshots = []
    # Exit and entry at same timestamp: exit margin cannot be reused until
    # the next timestamp. Entries are processed first.
    for ts in sorted(set(timeline) | set(observation_times)):
        actions = timeline.get(ts, [])
        for _, e in sorted((a for a in actions if a[0] == "entry"), key=lambda a: str(a[1]["id"])):
            if e["id"] in active:
                raise ValueError("duplicate active id")
            equity_realized = initial_capital + realized
            reserved = sum(p["margin"] for p in active.values())
            margin = equity_realized * margin_fraction
            if margin > equity_realized - reserved + 1e-9 or reserved + margin > equity_realized * max_margin_fraction + 1e-9:
                rejected.append({"id": e["id"], "ts": ts, "reason": "INSUFFICIENT_MARGIN"})
                continue
            active[e["id"]] = {"event": e, "margin": margin, "entry_ts": ts}
        for _, e in sorted((a for a in actions if a[0] == "exit"), key=lambda a: str(a[1]["id"])):
            p = active.pop(e["id"], None)
            if p is not None:
                realized += p["margin"] * e["leverage"] * e["net_return"]
        for _, e in (a for a in actions if a[0] == "partition_end"):
            if active.pop(e["id"], None) is not None:
                expired_partition_ids.append(e["id"])
        if ts not in observation_times:
            continue
        unrealized = 0.0
        exact = True
        missing = []
        stale = []
        for id_, p in active.items():
            e = p["event"]
            key = (e["symbol"], e["timeframe"])
            mark = observed_mark(histories[key], e["timeframe"], ts, max_age_ms=max_age_ms)
            if mark["price"] is None:
                exact = False
                missing.append(id_)
                continue
            if mark["status"] != "EXACT_CLOSE":
                exact = False
                stale.append({"id": id_, "status": mark["status"], "age_ms": mark["age_ms"]})
            direction = 1 if e["side"] == "LONG" else -1 if e["side"] == "SHORT" else None
            if direction is None:
                raise ValueError("invalid side")
            unrealized += p["margin"] * e["leverage"] * direction * (mark["price"] / e["entry_price"] - 1)
        reserved = sum(p["margin"] for p in active.values())
        positions = ([{"id": id_, "symbol": p["event"]["symbol"],
                       "timeframe": p["event"]["timeframe"],
                       "side": p["event"]["side"], "entry_price": p["event"]["entry_price"],
                       "leverage": p["event"]["leverage"], "margin": p["margin"]}
                      for id_, p in sorted(active.items())] if include_active_positions else None)
        snapshots.append({"ts": ts, "realized_pnl": realized,
                          "observed_unrealized_pnl": unrealized if exact else None,
                          "partial_observed_unrealized_pnl": unrealized,
                          "reserved_margin": reserved,
                          "available_capital_realized_basis": initial_capital + realized - reserved,
                          "strict_observed_equity": initial_capital + realized + unrealized if exact else None,
                          "missing_marks": missing, "non_exact_marks": stale,
                          "active_count": len(active),
                          **({"active_positions": positions} if include_active_positions else {})})
    return {"research_only": True, "not_exchange_mark_price": True,
            "no_liquidation_model": True, "rejected": rejected, "snapshots": snapshots,
            "expired_partition_ids": expired_partition_ids,
            "unclosed_ids": [id_ for id_, p in active.items() if p["event"]["reason"] == "END_OF_DATA"]}
