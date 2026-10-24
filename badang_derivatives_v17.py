"""BADANG Trading 1.7 — stateless, research-only OKX derivatives snapshot.

No database, background collector, automated order, or trading alert.
Trade imbalance is computed from up to 500 recent trades, NOT full CVD.
Current OI is NOT a 15m/1h OI change. All values are exchange snapshots.
"""
import time
from badang_derivatives_v15 import fetch, number, okx_symbol, vwap_from_candles


def research_v17(item, candles, session=None):
    symbol = item.get('symbol', '')
    inst = okx_symbol(symbol)
    vwap = vwap_from_candles(candles)
    result = {
        'version': '1.7.1', 'status': 'RESEARCH_ONLY', 'eligible_for_alert': False,
        'source_exchange': 'okx', 'instrument': inst, 'vwap': vwap,
        'collection': 'ON_DEMAND', 'database_required': False,
        'oi_change_15m_pct': None, 'oi_change_1h_pct': None,
        'oi_change_status': 'NOT_COMPUTED_NO_HISTORY',
        'complete_hour_cvd': False,
        'reason': '현재 시점 관측 자료만 제공; 검증된 매매 신호나 완전한 CVD가 아님',
    }
    if not inst:
        result.update(data_status='UNSUPPORTED_SYMBOL', errors={'symbol': 'UNSUPPORTED'})
        return result
    now_ms = int(time.time() * 1000)
    errors = {}
    oi = oi_ts = funding = None
    trades = []
    try:
        rows = fetch('/api/v5/public/open-interest', {'instType': 'SWAP', 'instId': inst}, session)
        row = next((r for r in rows if r.get('instId') == inst), None)
        oi = number(row.get('oi')) if row else None
        oi_ts = int(row.get('ts')) if row and row.get('ts') else None
        if oi is None or oi <= 0 or oi_ts is None or abs(now_ms - oi_ts) > 180000:
            oi = None
            errors['oi'] = 'MISSING_OR_STALE'
    except Exception as exc:
        errors['oi'] = type(exc).__name__
    try:
        rows = fetch('/api/v5/public/funding-rate', {'instId': inst}, session)
        row = next((r for r in rows if r.get('instId') == inst), None)
        funding = number(row.get('fundingRate')) if row else None
        if funding is None:
            errors['funding'] = 'MISSING'
    except Exception as exc:
        errors['funding'] = type(exc).__name__
    try:
        rows = fetch('/api/v5/market/trades', {'instId': inst, 'limit': '500'}, session)
        seen = set()
        for row in rows:
            tid = str(row.get('tradeId') or '')
            try:
                ts = int(row.get('ts'))
            except (ValueError, TypeError, OverflowError):
                continue
            side = row.get('side')
            size = number(row.get('sz'))
            if (not tid or tid in seen or ts > now_ms + 60000 or now_ms - ts > 3600000
                    or side not in ('buy', 'sell') or size is None or size <= 0):
                continue
            seen.add(tid)
            trades.append((side, size, ts))
        if not trades:
            errors['trades'] = 'NO_RECENT_TRADES'
    except Exception as exc:
        errors['trades'] = type(exc).__name__
    buy = sum(size for side, size, _ in trades if side == 'buy')
    sell = sum(size for side, size, _ in trades if side == 'sell')
    total = buy + sell
    imbalance = round((buy - sell) / total, 5) if total > 0 else None
    direction = item.get('recommendation')
    result.update({
        'observed_at_ms': now_ms, 'oi_contracts': oi, 'oi_exchange_ts_ms': oi_ts,
        'funding_rate': funding, 'trade_sample_count': len(trades),
        'sample_delta_contracts': round(buy - sell, 6) if total else None,
        'sample_imbalance': imbalance,
        'sample_span_seconds': round((max(t[2] for t in trades) - min(t[2] for t in trades)) / 1000, 1) if trades else None,
        'errors': errors, 'data_status': 'PARTIAL' if errors else 'OK',
        'checks': {
            'trend_aligned': item.get('trend_aligned') is True,
            'vwap_confirmed': direction in ('LONG', 'SHORT') and vwap.get('status') == 'OK'
                and vwap.get('price_position') == ('ABOVE' if direction == 'LONG' else 'BELOW'),
            'recent_trade_sample_agrees': direction in ('LONG', 'SHORT') and imbalance is not None
                and len(trades) >= 40 and (imbalance >= 0.12 if direction == 'LONG' else imbalance <= -0.12),
            'oi_history_available': False,
        },
    })
    return result
