"""Safe adapter for optional legacy research; never manufacture market evidence."""


def evaluate_optional_research(research_fn, item, candles, logger=None, symbol=""):
    """Return explicit unavailable evidence if the optional implementation is absent.

    Existing technical analysis remains usable; derivatives and sampled trade
    flow are not invented. A broken optional implementation is also isolated.
    """
    unavailable = {
        "status": "UNAVAILABLE",
        "eligible_for_alert": False,
        "reason": "OPTIONAL_RESEARCH_NOT_INSTALLED",
        "sample_imbalance": None,
        "trade_sample_count": 0,
    }
    if not callable(research_fn):
        return unavailable
    try:
        result = research_fn(item, candles)
        if not isinstance(result, dict):
            raise ValueError("optional research returned a non-dict result")
        return result
    except Exception as exc:
        if logger is not None:
            logger.warning("optional research failed for %s: %s", symbol, exc)
        return {**unavailable, "reason": "OPTIONAL_RESEARCH_FAILED"}
