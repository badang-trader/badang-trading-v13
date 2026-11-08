"""Read-only per-period performance for chronological holdout research.

Returns are unlevered trade returns, not account-level portfolio performance.
No claim of out-of-sample validity until the strategy is frozen before evaluation.
"""
from badang_research_holdout_partition_577 import partition_completed_trades
from badang_research_ledger_547 import summarize_nonoverlapping_trades

def holdout_performance(trades,split_index,total_bars):
    partition=partition_completed_trades(trades,split_index,total_bars)
    result={"split_index":split_index,"total_bars":total_bars,
            "boundary_excluded":partition["boundary_excluded"]}
    for period in ("development","holdout"):
        records=partition[period]
        result[period]={"completed_trades":len(records),
                        "metrics":summarize_nonoverlapping_trades(records) if records else None}
    result["performance_verified"]=False
    return result
