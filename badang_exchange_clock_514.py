"""Trusted Bitget public server clock for read-only research."""
from bitget_market_data import _get

def bitget_server_clock_ms(fetch=None):
    request=fetch if fetch is not None else _get
    data=request("/api/v2/public/time",{})
    if not isinstance(data,dict):
        raise ValueError("invalid_exchange_clock_response")
    raw=data.get("serverTime")
    if isinstance(raw,bool) or not isinstance(raw,(str,int)):
        raise ValueError("missing_exchange_clock")
    if isinstance(raw,str) and not raw.isdecimal():
        raise ValueError("invalid_exchange_clock")
    now=int(raw)
    if not 1000000000000 <= now < 100000000000000:
        raise ValueError("invalid_exchange_clock_range")
    return now
