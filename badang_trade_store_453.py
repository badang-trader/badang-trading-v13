"""Durable audit-only storage for Bitget REST trade snapshots.

A REST sample does not establish market-wide coverage or continuous CVD.
No trade data in this module is approved for trading scores.
"""
import json
import sqlite3
from pathlib import Path
from badang_trade_sample_450 import parse_fills
from badang_trade_overlap_452 import audit_pair


def _rows(payload):
    return payload.get('fillList') if isinstance(payload, dict) else payload


def _connect(path):
    db = sqlite3.connect(str(Path(path)), timeout=10)
    db.execute('PRAGMA busy_timeout=10000')
    db.execute('''CREATE TABLE IF NOT EXISTS trade_samples (
      symbol TEXT NOT NULL, fetched_ms INTEGER NOT NULL, payload TEXT NOT NULL,
      count INTEGER NOT NULL, PRIMARY KEY(symbol, fetched_ms))''')
    return db


def store_snapshot(path, symbol, payload, fetched_ms):
    """Validate, persist one sample, and audit against the previous persisted sample.

    Reject out-of-order or duplicate timestamps; use a transaction to avoid races.
    """
    parsed = parse_fills(payload, symbol, fetched_ms)
    symbol = parsed['symbol']
    rows = _rows(payload)
    with _connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT fetched_ms,payload FROM trade_samples WHERE symbol=? '
                              'ORDER BY fetched_ms DESC LIMIT 1', (symbol,)).fetchone()
        if previous and fetched_ms <= previous[0]:
            raise ValueError('Out-of-order or duplicate collection timestamp')
        audit = (audit_pair(json.loads(previous[1]), rows, symbol, previous[0], fetched_ms)
                 if previous else None)
        db.execute('INSERT INTO trade_samples(symbol,fetched_ms,payload,count) VALUES(?,?,?,?)',
                   (symbol, int(fetched_ms), json.dumps(rows, ensure_ascii=False), parsed['sample_count']))
    return {'sample': parsed, 'overlap_audit': audit, 'stored': True,
            'coverage_confirmed': False, 'is_cvd': False, 'used_in_trading_score': False}


def collection_status(path, symbol):
    """Operational diagnostics only. Count and gaps are NOT market coverage."""
    from badang_oi_history_441 import _valid_symbol
    symbol = _valid_symbol(symbol)
    with _connect(path) as db:
        records = db.execute('SELECT fetched_ms,count FROM trade_samples WHERE symbol=? '
                             'ORDER BY fetched_ms DESC LIMIT 1000', (symbol,)).fetchall()
    gaps = [records[i][0]-records[i+1][0] for i in range(len(records)-1)]
    return {'symbol': symbol, 'source_exchange': 'bitget',
            'snapshot_count': len(records), 'latest_fetched_ms': records[0][0] if records else None,
            'largest_collection_gap_ms': max(gaps) if gaps else None,
            'coverage_confirmed': False, 'is_cvd': False, 'used_in_trading_score': False,
            'warning': '수집 시점 사이 실제 체결 누락 여부는 REST 표본만으로 증명 불가'}
