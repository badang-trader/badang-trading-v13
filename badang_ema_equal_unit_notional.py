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
            for t in entries:
                accepted = (bool(t["ema_aligned"]) if filter_kind == "SAME_FRAME"
                            else htf.get(t["trade_id"]) == "HTF_ALIGNED")
                group = "SELECTED" if accepted else "EXCLUDED"
                raw = lookup[(t["symbol"], t["timeframe"])]["reversal_backtest"][strategy]["trades"][
                    int(t["trade_id"].rsplit(":", 1)[-1])]
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
            result.append({"strategy": strategy, "filter_kind": filter_kind,
                           "candidate_count": len(entries),
                           "selected": selected, "excluded": excluded,
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
