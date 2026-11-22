"""Research-only equal-unit-notional EMA selection diagnostic.

Each completed trade receives exactly one unit of notional, independently of
portfolio admission, overlap and margin. This is NOT an equal-exposure account
replay, nor proof of prospective signal quality. Censored trades are excluded
from mean returns and counted separately.
"""
import json
import math
from pathlib import Path
from badang_prospective_ema_eligibility import audit as ema_audit
from badang_htf_ema_candidate_selection import audit as htf_audit
from badang_causal_mark_lookup import FRAME_MS


def audit(cases, histories):
    report = ema_audit(cases, histories)
    htf = {r["trade_id"]: r["status"] for r in htf_audit(cases, histories)["results"]}
    lookup = {(c["symbol"], c["timeframe"]): c for c in cases}
    result = []
    for strategy in ("early", "confirmed"):
        entries = [t for r in report["results"] if r["strategy"] == strategy
                   for t in r["sample_entries"]]
        for filter_kind in ("SAME_FRAME", "HIGHER_FRAME"):
            groups = {"SELECTED": [], "EXCLUDED": []}
            censored = {"SELECTED": 0, "EXCLUDED": 0}
            intervals = {"SELECTED": [], "EXCLUDED": []}
            for t in entries:
                accepted = (bool(t["ema_aligned"]) if filter_kind == "SAME_FRAME"
                            else htf.get(t["trade_id"]) == "HTF_ALIGNED")
                group = "SELECTED" if accepted else "EXCLUDED"
                raw = lookup[(t["symbol"], t["timeframe"])]["reversal_backtest"][strategy]["trades"][
                    int(t["trade_id"].rsplit(":", 1)[-1])]
                key=(t["symbol"],t["timeframe"])
                candles=histories[key]
                entry_bar,exit_bar=int(raw["entry_bar"]),int(raw["exit_bar"])
                entry_ts=int(candles[entry_bar][0])
                end_ts=int(candles[exit_bar][0])+FRAME_MS[key[1]]
                if end_ts<=entry_ts:
                    raise AssertionError("invalid trade time interval")
                intervals[group].append((entry_ts,end_ts))
                value = raw["net_return"]
                if value is None:
                    censored[group] += 1
                else:
                    value = float(value)
                    if not math.isfinite(value):
                        raise AssertionError("nonfinite completed return")
                    groups[group].append(value)
            def summary(group):
                values = groups[group]
                n = len(values)
                mean = sum(values) / n if n else None
                variance = (sum((v-mean)**2 for v in values)/(n-1)) if n > 1 else None
                return {"closed_count": n, "censored_count": censored[group],
                        "unit_notional_mean_net_return": mean,
                        "unit_notional_sum_net_return": sum(values),
                        "sample_std": math.sqrt(variance) if variance is not None else None,
                        "standard_error": math.sqrt(variance/n) if variance is not None else None}
            selected, excluded = summary("SELECTED"), summary("EXCLUDED")
            def overlap_diagnostic():
                all_intervals=[(a,b,g) for g in intervals for a,b in intervals[g]]
                overlapping_pairs=0
                cross_group_pairs=0
                for i,(a,b,g) in enumerate(all_intervals):
                    for x,y,h in all_intervals[i+1:]:
                        if max(a,x)<min(b,y):
                            overlapping_pairs+=1
                            cross_group_pairs+=int(g!=h)
                return {"trade_intervals":len(all_intervals),
                        "overlapping_trade_pairs":overlapping_pairs,
                        "selected_excluded_overlap_pairs":cross_group_pairs,
                        "selected_mean_duration_hours":(sum((b-a) for a,b in intervals["SELECTED"])/len(intervals["SELECTED"])/3600000 if intervals["SELECTED"] else None),
                        "excluded_mean_duration_hours":(sum((b-a) for a,b in intervals["EXCLUDED"])/len(intervals["EXCLUDED"])/3600000 if intervals["EXCLUDED"] else None),
                        "causal_independence_established":False}
            # Welch uncertainty: independent-trade approximation only. Trades may
            # overlap in time and share market shocks; do not call this a valid
            # independent statistical significance test.
            uncertainty={"method":"WELCH_INDEPENDENT_TRADE_APPROXIMATION",
                         "valid_independent_inference":False,
                         "warning":"OVERLAPPING_CORRELATED_TRADES_AND_CENSORING"}
            if selected["closed_count"]>1 and excluded["closed_count"]>1:
                var_sel=selected["sample_std"]**2/selected["closed_count"]
                var_exc=excluded["sample_std"]**2/excluded["closed_count"]
                se=math.sqrt(var_sel+var_exc)
                denom=(var_sel**2/(selected["closed_count"]-1)+
                       var_exc**2/(excluded["closed_count"]-1))
                uncertainty.update({"difference_standard_error":se,
                                    "welch_degrees_of_freedom":(var_sel+var_exc)**2/denom if denom else None,
                                    "approx_normal_95_interval":[
                                        selected["unit_notional_mean_net_return"]-excluded["unit_notional_mean_net_return"]-1.96*se,
                                        selected["unit_notional_mean_net_return"]-excluded["unit_notional_mean_net_return"]+1.96*se],
                                    "interval_is_descriptive_only":True})
            else:
                uncertainty["status"]="INSUFFICIENT_COMPLETED_TRADES"
            result.append({"strategy": strategy, "filter_kind": filter_kind,
                           "candidate_count": len(entries),
                           "selected": selected, "excluded": excluded,
                           "difference_uncertainty":uncertainty,
                           "temporal_overlap_diagnostic":overlap_diagnostic(),
                           "closed_mean_difference": (
                               selected["unit_notional_mean_net_return"]-
                               excluded["unit_notional_mean_net_return"]
                               if selected["closed_count"] and excluded["closed_count"] else None),
                           "closed_and_censored_count_matches": (
                               sum(len(groups[g])+censored[g] for g in groups)==len(entries)),
                           "equal_unit_notional": True,
                           "equal_calendar_exposure": False,
                           "independent_out_of_sample": False})
    if len(result) != 4 or not all(x["closed_and_censored_count_matches"] for x in result):
        raise AssertionError("candidate classification count mismatch")
    return {"status": "DESCRIPTIVE_EQUAL_UNIT_NOTIONAL_NOT_EQUAL_EXPOSURE_ACCOUNT",
            "cutoff_ms": report["cutoff_ms"], "results": result,
            "warnings": ["CENSORED_RETURNS_EXCLUDED_NOT_ASSUMED_ZERO",
                         "SELECTED_AND_EXCLUDED_TRADES_DIFFER_IN_TIMING_AND_DURATION",
                         "NO_EQUAL_CALENDAR_EXPOSURE_OR_MARGIN_REPLAY",
                         "HISTORICAL_SELECTION_NOT_PROSPECTIVE_INDEPENDENT_TEST",
                         "NO_EXCHANGE_LIQUIDATION_OR_EXECUTION_CLAIM"]}


def main():
    folder = Path("research-output")
    cases = json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories = {(c["symbol"], c["timeframe"]):
                 json.loads((folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
                 for c in cases}
    result = audit(cases, histories)
    (folder/"bitget_ema_equal_unit_notional.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in result["results"]:
        print("EMA equal unit notional:", json.dumps(item))


if __name__ == "__main__":
    main()
