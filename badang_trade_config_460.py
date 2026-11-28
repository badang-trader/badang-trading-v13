"""Shared, read-only polling configuration for worker and status API.

Configuration equality does not establish market-wide trade coverage.
"""
import os


def poll_interval_seconds(raw=None):
    raw = os.getenv('BADANG_TRADE_POLL_SECONDS', '60') if raw is None else raw
    try:
        value = float(raw)
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Invalid polling interval') from None
    if not 15 <= value <= 3600 or not value.is_integer():
        raise ValueError('Polling interval must be a whole number from 15 to 3600 seconds')
    return int(value)


def poll_interval_ms(raw=None):
    return poll_interval_seconds(raw) * 1000
