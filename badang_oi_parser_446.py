"""Strict Bitget USDT futures open-interest response parser.

The endpoint returns a size in contracts; never confuse it with USD notional.
"""
import math


def parse_open_interest(payload):
    """Return a positive finite contract quantity, or raise ValueError.

    Accepts documented nested ``openInterestList`` and flat ``size`` shapes.
    Ambiguous multi-market responses are rejected rather than selecting a random row.
    """
    if isinstance(payload, dict):
        if 'openInterestList' in payload:
            rows = payload['openInterestList']
            if not isinstance(rows, list) or len(rows) != 1:
                raise ValueError('Ambiguous Bitget OI list')
            payload = rows[0]
        elif 'openInterest' in payload:
            payload = payload['openInterest']
    if isinstance(payload, list):
        if len(payload) != 1:
            raise ValueError('Ambiguous Bitget OI response')
        payload = payload[0]
    if isinstance(payload, dict):
        payload = payload.get('size')
    if isinstance(payload, bool) or payload is None:
        raise ValueError('Bitget OI field missing')
    try:
        value = float(payload)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Invalid Bitget OI value') from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Invalid Bitget OI value')
    return value
