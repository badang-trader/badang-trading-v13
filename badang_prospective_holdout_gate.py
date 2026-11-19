"""Strict prospective-only holdout eligibility gate.

A later collection timestamp is not proof of independent observations:
every evaluated bar must open after the frozen historical cutoff.
This module only certifies temporal separation, never profitability.
"""
from datetime import datetime,timezone

FROZEN_RESEARCH_CUTOFF_UTC='2026-11-19T06:01:00+00:00'

def cutoff_ms():
    return int(datetime.fromisoformat(FROZEN_RESEARCH_CUTOFF_UTC).timestamp()*1000)

def audit_nonoverlap(candidate_rows,*,cutoff=None,min_bars=1):
    if cutoff is None:cutoff=cutoff_ms()
    if min_bars<1:raise ValueError('min_bars must be positive')
    timestamps=[int(r[0]) for r in candidate_rows]
    if len(timestamps)!=len(set(timestamps)):
        raise ValueError('duplicate bar timestamps')
    if timestamps!=sorted(timestamps):
        raise ValueError('out of order bars')
    overlap=sum(ts<=cutoff for ts in timestamps)
    fresh=len(timestamps)-overlap
    eligible=overlap==0 and fresh>=min_bars
    return {'status':'TEMPORALLY_DISJOINT' if eligible else 'NOT_INDEPENDENT',
            'frozen_cutoff_utc':FROZEN_RESEARCH_CUTOFF_UTC,
            'overlap_or_cutoff_bars':overlap,'new_bars':fresh,
            'minimum_required_bars':min_bars,
            'independent_period_eligible':eligible,
            'strategy_profitable':'NOT_ESTABLISHED',
            'warning':'NO_SELECTION_ON_NEW_DATA; REQUIRE FROZEN_RULES_AND_SUFFICIENT_SAMPLE'}
