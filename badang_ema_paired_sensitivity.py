"""Stage 87: paired same-timestamp EMA capital sensitivity, research only.

Uses existing prospective same-timeframe EMA eligibility; does not claim
prospective profitability, intrabar MDD, or exchange liquidation.
"""
import json
from pathlib import Path
from badang_prospective_ema_eligibility import audit
from badang_censored_equity_replay import replay
from badang_synchronized_ohlc_stress import stress_snapshots
from badang_htf_ema_candidate_selection import audit as htf_audit
from badang_causal_mark_lookup import FRAME_MS

def run(cases,histories,filter_kind="SAME_FRAME"):
    if filter_kind not in ("SAME_FRAME","HIGHER_FRAME"):
        raise ValueError("invalid EMA filter kind")
    report=audit(cases,histories)
    htf_status={x["trade_id"]:x["status"] for x in htf_audit(cases,histories)["results"]} if filter_kind=="HIGHER_FRAME" else {}
    by_key={(c["symbol"],c["timeframe"]):c for c in cases}
    outputs=[]
    for strategy in ("early","confirmed"):
        selected=[t for r in report["results"] if r["strategy"]==strategy for t in r["sample_entries"]]
        modes={}
        for mode in ("ALL","EMA_ALIGNED"):
            events=[]
            for t in selected:
                if mode=="EMA_ALIGNED" and not (t["ema_aligned"] if filter_kind=="SAME_FRAME" else htf_status.get(t["trade_id"])=="HTF_ALIGNED"):continue
                key=(t["symbol"],t["timeframe"])
                raw=by_key[key]["reversal_backtest"][strategy]["trades"][int(t["trade_id"].rsplit(":",1)[-1])]
                rows=histories[key]
                a,b=int(raw["entry_bar"]),int(raw["exit_bar"])
                reason="CLOSED" if raw["net_return"] is not None else raw["exit_reason"]
                e={"id":t["trade_id"],"symbol":key[0],"timeframe":key[1],
                   "side":t["side"],"entry_ts":int(rows[a][0]),
                   "entry_price":float(raw["entry"]),"reason":reason}
                if reason=="CLOSED":
                    e.update(exit_ts=int(rows[b][0])+FRAME_MS[key[1]],net_return=float(raw["net_return"]))
                if reason=="END_OF_PARTITION":
                    e["partition_end_ts"]=int(rows[b][0])+FRAME_MS[key[1]]
                events.append(e)
            modes[mode]=events
        relevant={(e["symbol"],e["timeframe"]) for events in modes.values() for e in events}
        # Same timeline for both arms; close observations are not forward-filled.
        times=sorted({int(r[0])+FRAME_MS[k[1]] for k in relevant for r in histories[k]
                      if int(r[0])>report["cutoff_ms"]})
        for lev in (1,2,3):
            for fraction in (.03,.05):
                for cap in (.20,.30):
                    arms={}
                    for mode,events in modes.items():
                        out=replay([{**e,"leverage":float(lev)} for e in events],
                                   histories,times,initial_capital=10000.,
                                   margin_fraction=fraction,max_margin_fraction=cap,
                                   include_active_positions=True)
                        snaps={s["ts"]:s for s in out["snapshots"]}
                        arms[mode]={"snapshots":snaps,"rejected":len(out["rejected"]),
                                    "expired_partition_count":len(out["expired_partition_ids"]),
                                    "unclosed_count":len(out["unclosed_ids"]),
                                    "stress":stress_snapshots(out["snapshots"],histories)}
                    common=sorted(set(arms["ALL"]["snapshots"])&set(arms["EMA_ALIGNED"]["snapshots"]))
                    exact=[ts for ts in common if all(arms[m]["snapshots"][ts]["strict_observed_equity"] is not None
                                                       for m in arms)]
                    # Pair both arms on the exact same observation timestamps.
                    for mode in arms:
                        arms[mode]["stress"]=stress_snapshots(
                            list(arms[mode]["snapshots"].values()),histories,
                            observation_times=exact)
                    def metrics(mode):
                        arm=arms[mode];snaps=arm["snapshots"]
                        realized_peak=10000.;realized_mdd=0.
                        exact_peak=10000.;exact_mdd=0.
                        for s in snaps.values():
                            balance=10000.+s["realized_pnl"]
                            realized_peak=max(realized_peak,balance)
                            realized_mdd=max(realized_mdd,(realized_peak-balance)/realized_peak)
                        # Only common exact timestamps are comparable. Not intrabar MDD.
                        for ts in exact:
                            eq=snaps[ts]["strict_observed_equity"]
                            exact_peak=max(exact_peak,eq)
                            exact_mdd=max(exact_mdd,(exact_peak-eq)/exact_peak)
                        # Compare exposure on exactly the same paired observation clock.
                        observations=[snaps[ts] for ts in exact]
                        n=len(observations)
                        avg_active=sum(s["active_count"] for s in observations)/n if n else None
                        avg_reserved=sum(s["reserved_margin"] for s in observations)/n if n else None
                        avg_notional=sum(sum(p["margin"]*p["leverage"] for p in s["active_positions"])
                                         for s in observations)/n if n else None
                        active_observations=sum(s["active_count"]>0 for s in observations)
                        last=snaps[exact[-1]] if exact else None
                        return {"realized_mdd":realized_mdd,
                                "synchronized_ohlc_stress":arm["stress"],
                                "common_exact_close_mdd_lower_bound":exact_mdd,
                                "exposure_on_common_clock":{
                                    "observation_count":n,
                                    "mean_active_positions":avg_active,
                                    "mean_reserved_margin":avg_reserved,
                                    "mean_gross_notional":avg_notional,
                                    "observations_with_positions":active_observations,
                                    "exposure_adjusted_profitability_proven":False},
                                "rejected":arm["rejected"],
                                "expired_partition_count":arm["expired_partition_count"],
                                "unclosed_count":arm["unclosed_count"],
                                "at_last_common_exact":({k:last[k] for k in (
                                    "ts","realized_pnl","observed_unrealized_pnl",
                                    "strict_observed_equity","reserved_margin",
                                    "available_capital_realized_basis","active_count")} if last else None)}
                    a,b=metrics("ALL"),metrics("EMA_ALIGNED")
                    if a["synchronized_ohlc_stress"]["exact_observations"]!=len(exact) or b["synchronized_ohlc_stress"]["exact_observations"]!=len(exact):
                        raise AssertionError("paired OHLC stress observations differ")
                    # Exposure-normalized descriptive comparison; not a counterfactual replay.
                    def normalized(m):
                        exposure=m["exposure_on_common_clock"]["mean_gross_notional"]
                        if exposure is None or exposure<=0:
                            return {"status":"ZERO_EXPOSURE_NOT_COMPARABLE",
                                    "stress_mdd_per_10000_mean_notional":None,
                                    "close_mdd_per_10000_mean_notional":None}
                        factor=exposure/10000.
                        return {"status":"DESCRIPTIVE_ONLY",
                                "stress_mdd_per_10000_mean_notional":m["synchronized_ohlc_stress"]["synchronized_ohlc_stress_mdd"]/factor,
                                "close_mdd_per_10000_mean_notional":m["common_exact_close_mdd_lower_bound"]/factor}
                    normalized_all,normalized_ema=normalized(a),normalized(b)
                    # True chronological account rerun with equal fixed margin PER
                    # accepted trade, subject to the same aggregate margin cap.
                    # This does not force equal aggregate exposure at each timestamp.
                    fixed_arms={}
                    for mode,events in modes.items():
                        fixed_out=replay([{**e,"leverage":float(lev)} for e in events],
                                         histories,times,initial_capital=10000.,
                                         margin_fraction=fraction,max_margin_fraction=cap,
                                         fixed_margin_per_trade=10000.*fraction,
                                         include_active_positions=True)
                        fixed_snaps={s["ts"]:s for s in fixed_out["snapshots"]}
                        fixed_arms[mode]={"snaps":fixed_snaps,
                                          "rejected":len(fixed_out["rejected"]),
                                          "unclosed":len(fixed_out["unclosed_ids"]),
                                          "expired":len(fixed_out["expired_partition_ids"])}
                    fixed_exact=[ts for ts in exact if all(
                        fixed_arms[mode]["snaps"][ts]["strict_observed_equity"] is not None
                        for mode in fixed_arms)]
                    def fixed_summary(mode):
                        arm=fixed_arms[mode];snap=arm["snaps"]
                        peak_realized=peak_close=10000.
                        realized_mdd=close_mdd=0.
                        for s in snap.values():
                            eq=10000.+s["realized_pnl"]
                            peak_realized=max(peak_realized,eq)
                            realized_mdd=max(realized_mdd,(peak_realized-eq)/peak_realized)
                        for ts in fixed_exact:
                            eq=snap[ts]["strict_observed_equity"]
                            peak_close=max(peak_close,eq)
                            close_mdd=max(close_mdd,(peak_close-eq)/peak_close)
                        obs=[snap[ts] for ts in fixed_exact]
                        last=obs[-1] if obs else None
                        stress=stress_snapshots(list(snap.values()),histories,
                                                observation_times=fixed_exact)
                        return {"fixed_margin_per_trade":10000.*fraction,
                                "realized_mdd":realized_mdd,
                                "common_exact_close_mdd":close_mdd,
                                "synchronized_ohlc_stress_mdd":stress["synchronized_ohlc_stress_mdd"],
                                "mean_gross_notional":(sum(sum(p["margin"]*p["leverage"] for p in s["active_positions"]) for s in obs)/len(obs) if obs else None),
                                "mean_reserved_margin":(sum(s["reserved_margin"] for s in obs)/len(obs) if obs else None),
                                "rejected":arm["rejected"],"unclosed":arm["unclosed"],
                                "expired_partition":arm["expired"],
                                "last_exact":({k:last[k] for k in ("ts","realized_pnl",
                                   "observed_unrealized_pnl","strict_observed_equity",
                                   "reserved_margin","active_count")} if last else None)}
                    fixed_all=fixed_summary("ALL")
                    fixed_ema=fixed_summary("EMA_ALIGNED")
                    if not fixed_exact:
                        raise AssertionError("no exact fixed-budget common observations")
                    for arm in (fixed_all,fixed_ema):
                        if arm["last_exact"]["reserved_margin"] > cap*max(0.,10000.+arm["last_exact"]["realized_pnl"])+1e-5:
                            raise AssertionError("fixed-budget margin cap breached")
                    # Compare ACTUAL timestamp-by-timestamp exposure, not only
                    # averages. Zero EMA exposure with positive ALL exposure is
                    # infeasible to match without inventing additional trades.
                    gaps=[]
                    zero_ema_positive_all=0
                    exact_match=0
                    positive_both=0
                    for ts in fixed_exact:
                        def gross(mode):
                            return sum(p["margin"]*p["leverage"] for p in
                                       fixed_arms[mode]["snaps"][ts]["active_positions"])
                        gross_all,gross_ema=gross("ALL"),gross("EMA_ALIGNED")
                        gaps.append(gross_ema-gross_all)
                        zero_ema_positive_all+=int(gross_ema==0 and gross_all>0)
                        exact_match+=int(abs(gross_ema-gross_all)<1e-8)
                        positive_both+=int(gross_ema>0 and gross_all>0)
                    exposure_gap_diagnostic={
                        "common_exact_observations":len(fixed_exact),
                        "exact_equal_exposure_observations":exact_match,
                        "zero_ema_with_positive_all_observations":zero_ema_positive_all,
                        "both_positive_exposure_observations":positive_both,
                        "mean_absolute_notional_gap":sum(abs(g) for g in gaps)/len(gaps),
                        "maximum_absolute_notional_gap":max(abs(g) for g in gaps),
                        "mean_signed_notional_gap":sum(gaps)/len(gaps),
                        "equal_exposure_counterfactual_executed":False,
                        "warning":"NO_SYNTHETIC_TRADES_OR_MARGIN_CAP_BREACH_TO_FORCE_EQUAL_EXPOSURE"}
                    fixed_budget={"status":"EQUAL_FIXED_MARGIN_PER_ACCEPTED_TRADE_NOT_EQUAL_TIME_EXPOSURE",
                                  "common_exact_observations":len(fixed_exact),
                                  "timewise_exposure_gap":exposure_gap_diagnostic,
                                  "all":fixed_all,"ema":fixed_ema,
                                  "mean_notional_gap_ema_minus_all":fixed_ema["mean_gross_notional"]-fixed_all["mean_gross_notional"],
                                  "independent_signal_quality_proven":False}
                    outputs.append({"strategy":strategy,"leverage":lev,"margin_fraction":fraction,
                                    "max_margin_fraction":cap,"common_exact_observations":len(exact),
                                    "all":a,"ema":b,
                                    "fixed_per_trade_budget_replay":fixed_budget,
                                    "exposure_normalized_descriptive":{
                                        "all":normalized_all,"ema":normalized_ema,
                                        "causal_signal_quality_established":False,
                                        "warning":"RATIO_OF_PATH_DEPENDENT_MDD_TO_MEAN_NOTIONAL_NOT_AN_EQUAL_EXPOSURE_REPLAY"},
                                    "ema_minus_all_equity":(
                                        b["at_last_common_exact"]["strict_observed_equity"]-
                                        a["at_last_common_exact"]["strict_observed_equity"] if exact else None)})
    # Hard fail on arithmetic errors; a green CI must not hide broken account identities.
    if len(outputs)!=24:
        raise AssertionError(f"expected 24 scenarios, got {len(outputs)}")
    expected={(strategy,lev,fraction,cap) for strategy in ("early","confirmed")
              for lev in (1,2,3) for fraction in (.03,.05) for cap in (.20,.30)}
    actual={(s["strategy"],s["leverage"],s["margin_fraction"],s["max_margin_fraction"]) for s in outputs}
    if actual!=expected:
        raise AssertionError("scenario grid missing or duplicated")
    for s in outputs:
        for mode in ("all","ema"):
            metrics=s[mode]
            last=metrics["at_last_common_exact"]
            if last is None:
                raise AssertionError("no comparable exact close")
            realized=last["realized_pnl"]
            unrealized=last["observed_unrealized_pnl"]
            equity=last["strict_observed_equity"]
            reserved=last["reserved_margin"]
            available=last["available_capital_realized_basis"]
            if abs(equity-(10000.+realized+unrealized))>1e-7:
                raise AssertionError("equity accounting mismatch")
            if abs(available-(10000.+realized-reserved))>1e-7:
                raise AssertionError("available capital accounting mismatch")
            if reserved < -1e-7 or reserved>max(0.,10000.+realized)*s["max_margin_fraction"]+1e-5:
                raise AssertionError("margin cap breached")
            exposure=metrics["exposure_on_common_clock"]
            if exposure["observation_count"]!=s["common_exact_observations"]:
                raise AssertionError("exposure observation count mismatch")
            if exposure["mean_reserved_margin"] < -1e-8 or exposure["mean_gross_notional"] < -1e-8:
                raise AssertionError("invalid average exposure")
            if not 0<=exposure["observations_with_positions"]<=exposure["observation_count"]:
                raise AssertionError("invalid active observation count")
            if not 0<=metrics["realized_mdd"]<=1 or not 0<=metrics["common_exact_close_mdd_lower_bound"]<=1:
                raise AssertionError("invalid drawdown")
        difference=s["ema"]["at_last_common_exact"]["strict_observed_equity"]-s["all"]["at_last_common_exact"]["strict_observed_equity"]
        if abs(difference-s["ema_minus_all_equity"])>1e-7:
            raise AssertionError("paired equity difference mismatch")
    return {"status":"RESEARCH_ONLY_NOT_INDEPENDENT_PROFITABILITY",
            "filter_kind":filter_kind,
            "cutoff_ms":report["cutoff_ms"],"scenarios":outputs,
            "warnings":["FILTER_KIND_IS_RESEARCH_ONLY",
                        "EXPOSURE_METRICS_ARE_DESCRIPTIVE_NOT_CAUSAL_EFFECT",
                        "EXPOSURE_NORMALIZED_MDD_RATIO_IS_NOT_A_COUNTERFACTUAL",
                        "COMMON_EXACT_CLOSE_MDD_IS_OBSERVATION_LOWER_BOUND",
                        "SYNCHRONIZED_OHLC_STRESS_IS_HYPOTHETICAL_NOT_TRUE_INTRABAR_MDD",
                        "NO_EXCHANGE_LIQUIDATION_MODEL",
                        "HISTORICAL_SIGNAL_SELECTION_NOT_PROSPECTIVELY_VALIDATED"]}
def main():
    folder=Path("research-output")
    cases=json.loads((folder/"bitget_reversal_candidates.json").read_text(encoding="utf-8"))["cases"]
    histories={(c["symbol"],c["timeframe"]):json.loads(
        (folder/f'bitget_{c["symbol"]}_{c["timeframe"]}.json').read_text(encoding="utf-8"))["candles"]
        for c in cases}
    result=run(cases,histories)
    (folder/"bitget_ema_paired_sensitivity.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    for s in result["scenarios"]:
        print("paired EMA sensitivity:",json.dumps(s))
    higher=run(cases,histories,filter_kind="HIGHER_FRAME")
    (folder/"bitget_htf_ema_paired_sensitivity.json").write_text(
        json.dumps(higher,ensure_ascii=False,indent=2),encoding="utf-8")
    for s in higher["scenarios"]:
        print("paired HTF EMA sensitivity:",json.dumps(s))
    # Additional equal-unit trade comparison, separate from account replay.
    from badang_ema_equal_unit_notional import audit as unit_audit
    unit_result=unit_audit(cases,histories)
    (folder/"bitget_ema_equal_unit_notional.json").write_text(
        json.dumps(unit_result,ensure_ascii=False,indent=2),encoding="utf-8")
    for item in unit_result["results"]:
        print("EMA equal unit notional:",json.dumps(item))
if __name__=="__main__":main()
