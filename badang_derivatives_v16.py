"""BADANG 1.6: research-only persistent OKX OI and deduplicated trade flow.

Snapshots are observational. OI deltas are available only when sufficiently spaced
observations exist. Trade flow covers observed public trades only, NOT full CVD.
No trading alert is authorized by this module.
"""
import math
import time
from datetime import datetime, timezone

from badang_derivatives_v15 import (fetch, number, okx_symbol,
                                    vwap_from_candles)

DDL = [
    """CREATE TABLE IF NOT EXISTS badang_v16_oi (
        exchange TEXT NOT NULL, instrument TEXT NOT NULL,
        observed_at_ms BIGINT NOT NULL, exchange_ts_ms BIGINT,
        contracts DOUBLE PRECISION NOT NULL,
        PRIMARY KEY(exchange, instrument, observed_at_ms))""",
    """CREATE INDEX IF NOT EXISTS badang_v16_oi_lookup
        ON badang_v16_oi(exchange, instrument, observed_at_ms DESC)""",
    """CREATE TABLE IF NOT EXISTS badang_v16_trades (
        exchange TEXT NOT NULL, instrument TEXT NOT NULL,
        trade_id TEXT NOT NULL, exchange_ts_ms BIGINT NOT NULL,
        side TEXT NOT NULL, size_contracts DOUBLE PRECISION NOT NULL,
        observed_at_ms BIGINT NOT NULL,
        PRIMARY KEY(exchange, instrument, trade_id))""",
    """CREATE INDEX IF NOT EXISTS badang_v16_trades_lookup
        ON badang_v16_trades(exchange, instrument, exchange_ts_ms DESC)""",
]


def _ms(value):
    try:
        result = int(value)
        return result if result > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _history(conn, instrument, now_ms, oi):
    """Use earliest sample in [window, 2*window] to avoid pretending short gaps are 1h."""
    changes = {}
    with conn.cursor() as cur:
        for label, window in [('15m', 900000), ('1h', 3600000)]:
            cur.execute("""SELECT contracts, observed_at_ms FROM badang_v16_oi
                WHERE exchange='okx' AND instrument=%s
                AND observed_at_ms BETWEEN %s AND %s
                ORDER BY observed_at_ms DESC LIMIT 1""",
                (instrument, now_ms - 2 * window, now_ms - window))
            row = cur.fetchone()
            if row and row[0] and row[0] > 0:
                changes[label] = {'pct': round((oi / row[0] - 1) * 100, 4),
                                  'baseline_ms': row[1], 'elapsed_minutes': round((now_ms - row[1]) / 60000, 1)}
            else:
                changes[label] = None
    return changes


def _persist(db_connect, instrument, now_ms, oi, oi_ts, trades):
    conn = db_connect()
    try:
        with conn:
            with conn.cursor() as cur:
                for ddl in DDL:
                    cur.execute(ddl)
                if oi is not None:
                    cur.execute("""INSERT INTO badang_v16_oi
                        (exchange,instrument,observed_at_ms,exchange_ts_ms,contracts)
                        VALUES ('okx',%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                        (instrument, now_ms, oi_ts, oi))
                new_count = 0
                for tid, ts, side, size in trades:
                    cur.execute("""INSERT INTO badang_v16_trades
                        (exchange,instrument,trade_id,exchange_ts_ms,side,size_contracts,observed_at_ms)
                        VALUES ('okx',%s,%s,%s,%s,%s,%s)
                        ON CONFLICT DO NOTHING RETURNING trade_id""",
                        (instrument, tid, ts, side, size, now_ms))
                    if cur.fetchone():
                        new_count += 1
                # Observed 1h flow is partial if scans are not continuous.
                cur.execute("""SELECT side, size_contracts FROM badang_v16_trades
                    WHERE exchange='okx' AND instrument=%s AND exchange_ts_ms >= %s""",
                    (instrument, now_ms - 3600000))
                recent = cur.fetchall()
                buy = sum(size for side, size in recent if side == 'buy')
                sell = sum(size for side, size in recent if side == 'sell')
                cur.execute("""SELECT COUNT(DISTINCT date_trunc('minute',
                    to_timestamp(exchange_ts_ms / 1000.0))) FROM badang_v16_trades
                    WHERE exchange='okx' AND instrument=%s AND exchange_ts_ms >= %s""",
                    (instrument, now_ms - 3600000))
                minute_coverage = cur.fetchone()[0]
            changes = _history(conn, instrument, now_ms, oi) if oi is not None else {'15m': None, '1h': None}
        return {'status': 'OK', 'new_trades': new_count, 'observed_trade_count_1h': len(recent),
                'observed_delta_contracts_1h': round(buy - sell, 6),
                'observed_minutes_1h': minute_coverage,
                'complete_hour_cvd': False, 'oi_changes': changes}
    finally:
        conn.close()


def research_v16(item, candles, db_connect=None, session=None):
    """All errors are represented as unavailable, never interpreted as a signal."""
    symbol = item.get('symbol', '')
    inst = okx_symbol(symbol)
    vwap = vwap_from_candles(candles)
    result = {'status': 'RESEARCH_ONLY', 'eligible_for_alert': False,
              'source_exchange': 'okx', 'instrument': inst, 'vwap': vwap,
              'reason': '관측 데이터 및 성과 검증 불충분: 자동 알림 비활성'}
    if not inst:
        result['data_status'] = 'UNSUPPORTED_SYMBOL'
        return result
    now_ms = int(time.time() * 1000)
    oi = oi_ts = None
    trades = []
    funding = None
    errors = {}
    try:
        rows = fetch('/api/v5/public/open-interest', {'instType': 'SWAP', 'instId': inst}, session)
        row = next((r for r in rows if r.get('instId') == inst), None)
        oi = number(row.get('oi')) if row else None
        oi_ts = _ms(row.get('ts')) if row else None
        if oi is None or oi <= 0 or oi_ts is None or abs(now_ms - oi_ts) > 180000:
            oi = None
            errors['oi'] = 'MISSING_OR_STALE'
    except Exception as exc:
        errors['oi'] = type(exc).__name__
    try:
        rows = fetch('/api/v5/public/funding-rate', {'instId': inst}, session)
        row = next((r for r in rows if r.get('instId') == inst), None)
        funding = number(row.get('fundingRate')) if row else None
    except Exception as exc:
        errors['funding'] = type(exc).__name__
    try:
        rows = fetch('/api/v5/market/trades', {'instId': inst, 'limit': '500'}, session)
        seen = set()
        for row in rows:
            tid = str(row.get('tradeId') or '')
            ts = _ms(row.get('ts'))
            side = row.get('side')
            size = number(row.get('sz'))
            if (not tid or tid in seen or ts is None or
                abs(now_ms - ts) > 3600000 or side not in ('buy', 'sell') or
                size is None or size <= 0):
                continue
            seen.add(tid)
            trades.append((tid, ts, side, size))
    except Exception as exc:
        errors['trades'] = type(exc).__name__
    buy = sum(x[3] for x in trades if x[2] == 'buy')
    sell = sum(x[3] for x in trades if x[2] == 'sell')
    total = buy + sell
    result.update({'observed_at_ms': now_ms, 'oi_contracts': oi,
                   'funding_rate': funding, 'trade_sample_count': len(trades),
                   'sample_delta_contracts': round(buy - sell, 6) if total else None,
                   'sample_imbalance': round((buy - sell) / total, 5) if total else None,
                   'errors': errors, 'data_status': 'PARTIAL' if errors else 'OK'})
    if db_connect is not None:
        try:
            result['history'] = _persist(db_connect, inst, now_ms, oi, oi_ts, trades)
        except Exception as exc:
            result['history'] = {'status': 'UNAVAILABLE', 'reason': type(exc).__name__}
    else:
        result['history'] = {'status': 'UNAVAILABLE', 'reason': 'DATABASE_NOT_CONFIGURED'}
    direction = item.get('recommendation')
    imbalance = result['sample_imbalance']
    result['checks'] = {
        'trend_aligned': item.get('trend_aligned') is True,
        'vwap_confirmed': direction in ('LONG', 'SHORT') and vwap.get('status') == 'OK'
            and vwap.get('price_position') == ('ABOVE' if direction == 'LONG' else 'BELOW'),
        'trade_sample_confirmed': direction in ('LONG', 'SHORT') and imbalance is not None
            and len(trades) >= 40 and (imbalance >= 0.12 if direction == 'LONG' else imbalance <= -0.12),
        'oi_history_available': result['history'].get('status') == 'OK'
            and any(x is not None for x in result['history']['oi_changes'].values()),
    }
    return result
