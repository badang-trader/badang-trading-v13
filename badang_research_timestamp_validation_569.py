"""Require ordered, unique, uniformly spaced historical timestamps.

Only applies to complete timestamped research candles; minimalist fixtures
without timestamps remain supported by the separate OHLC validator.
"""
def validate_research_timestamps(candles,interval_ms):
    if not isinstance(interval_ms,int) or isinstance(interval_ms,bool) or interval_ms<=0:
        raise ValueError("Invalid candle interval")
    previous=None
    for index,bar in enumerate(candles):
        if not isinstance(bar,dict):
            raise ValueError("Invalid candle")
        timestamp=bar.get("timestamp")
        if not isinstance(timestamp,int) or isinstance(timestamp,bool) or timestamp<0:
            raise ValueError("Invalid timestamp at index "+str(index))
        if timestamp%interval_ms!=0:
            raise ValueError("Off-grid timestamp at index "+str(index))
        if previous is not None and timestamp-previous!=interval_ms:
            raise ValueError("Missing, duplicate or unsorted candle at index "+str(index))
        previous=timestamp
    return True
