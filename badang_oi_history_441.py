"""Bitget-only, on-demand OI observation history. Not a continuous collector.

SQLite is local and may be ephemeral on hosting platforms. No inference is made
when a valid observation near the requested comparison time is unavailable.
"""
import math
import os
import re
import sqlite3
from contextlib import closing
import time
from pathlib import Path

SCHEMA = '''CREATE TABLE IF NOT EXISTS oi_observations (
    symbol TEXT NOT NULL, exchange TEXT NOT NULL, observed_ms INTEGER NOT NULL,
    oi REAL NOT NULL CHECK(oi > 0), PRIMARY KEY(symbol, exchange, observed_ms)
)'''


def _valid_symbol(symbol):
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9]{2,25}USDT', symbol):
        raise ValueError('Invalid Bitget futures symbol')
    return symbol


def record_oi(db_path, symbol, oi, observed_ms=None, exchange='bitget'):
    symbol = _valid_symbol(symbol)
    if exchange != 'bitget':
        raise ValueError('Cross-exchange OI is not permitted')
    oi = float(oi)
    if not math.isfinite(oi) or oi <= 0:
        raise ValueError('Invalid OI observation')
    now = int(time.time() * 1000)
    observed_ms = now if observed_ms is None else int(observed_ms)
    if observed_ms > now + 60_000 or observed_ms < now - 86_400_000:
        raise ValueError('OI observation timestamp out of range')
    with closing(sqlite3.connect(str(db_path), timeout=5)) as con, con:
        con.execute(SCHEMA)
        con.execute('INSERT OR IGNORE INTO oi_observations VALUES (?, ?, ?, ?)',
                    (symbol, exchange, observed_ms, oi))
        con.execute('DELETE FROM oi_observations WHERE observed_ms < ?', (now - 86_400_000,))
    return {'symbol': symbol, 'exchange': exchange, 'observed_ms': observed_ms, 'oi': oi}


def oi_changes(db_path, symbol, now_ms=None, tolerance_ms=90_000, freshness_ms=180_000):
    symbol = _valid_symbol(symbol)
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    result = {'source_exchange': 'bitget', 'symbol': symbol, 'status': 'INSUFFICIENT_HISTORY',
              'collection': 'ON_DEMAND', 'storage_durable': False,
              'oi_change_15m_pct': None, 'oi_change_1h_pct': None,
              'reason': '관측 시점에 충분한 Bitget OI 기록이 필요함'}
    if not Path(db_path).exists():
        return result
    with closing(sqlite3.connect(str(db_path), timeout=5)) as con, con:
        con.execute(SCHEMA)
        rows = con.execute('SELECT observed_ms, oi FROM oi_observations WHERE symbol=? AND exchange=? AND observed_ms<=? ORDER BY observed_ms DESC LIMIT 2000',
                           (symbol, 'bitget', now_ms)).fetchall()
    if not rows or now_ms - rows[0][0] > freshness_ms:
        result['status'] = 'STALE_OR_MISSING_CURRENT'
        return result
    latest_t, latest_oi = rows[0]
    result.update(current_oi=latest_oi, current_observed_ms=latest_t)
    for label, period in [('15m', 900_000), ('1h', 3_600_000)]:
        target = latest_t - period
        matches = [(abs(t-target), t, oi) for t, oi in rows[1:] if abs(t-target) <= tolerance_ms]
        if matches:
            _, old_t, old_oi = min(matches)
            result['oi_change_' + label + '_pct'] = round((latest_oi / old_oi - 1) * 100, 5)
            result[label + '_baseline_ms'] = old_t
    if result['oi_change_15m_pct'] is not None and result['oi_change_1h_pct'] is not None:
        result.update(status='HISTORY_AVAILABLE', reason='동일 거래소 관측값으로 계산; 연속 수집 및 전체 CVD 검증은 별개')
    elif any(result['oi_change_' + k + '_pct'] is not None for k in ('15m','1h')):
        result.update(status='PARTIAL_HISTORY', reason='일부 기간에만 비교 가능한 관측값 존재')
    return result


def observe_bitget_oi(db_path, symbol):
    """One network request on explicit invocation; no background scheduling."""
    from bitget_market_data import _get
    rows = _get('/api/v2/mix/market/open-interest',
                {'symbol': _valid_symbol(symbol), 'productType': 'USDT-FUTURES'})
    from badang_oi_parser_446 import parse_open_interest
    oi = parse_open_interest(rows)
    record_oi(db_path, symbol, oi)
    return oi_changes(db_path, symbol)
