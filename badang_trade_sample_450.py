"""Read-only Bitget recent-fill sample. NOT continuous or market-complete CVD.

A bounded REST response is a *sample* of executions, not an audited
interval. This module never promotes it to a directional trading signal.
"""
import math
import time
from badang_oi_history_441 import _valid_symbol


def parse_fills(payload, symbol, fetched_ms=None):
    symbol = _valid_symbol(symbol)
    fetched_ms = int(time.time()*1000) if fetched_ms is None else int(fetched_ms)
    rows = payload.get('fillList') if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError('Invalid fills payload')
    if len(rows) > 100:
        raise ValueError('Oversized trade sample')
    seen = set()
    missing_ids = 0
    buys = sells = 0.0
    valid = 0
    first = last = None
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError('Malformed fill')
        if item.get('symbol') and str(item['symbol']).upper() != symbol:
            raise ValueError('Mixed-symbol fill payload')
        side = str(item.get('side', '')).lower()
        if side not in ('buy', 'sell'):
            raise ValueError('Unknown aggressor side')
        try:
            size = float(item['size'])
            stamp = int(item.get('ts', item.get('timestamp')))
        except (KeyError, ValueError, TypeError, OverflowError):
            raise ValueError('Invalid fill fields') from None
        if not math.isfinite(size) or size <= 0 or stamp <= 0 or stamp > fetched_ms + 60000:
            raise ValueError('Invalid fill value or timestamp')
        trade_id = item.get('tradeId') or item.get('id')
        if trade_id is None:
            missing_ids += 1
        if trade_id is not None:
            if trade_id in seen:
                raise ValueError('Duplicate trade ID')
            seen.add(trade_id)
        if side == 'buy':
            buys += size
        else:
            sells += size
        valid += 1
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
    age_ms = fetched_ms - last if last is not None else None
    freshness = ('EMPTY' if not valid else 'STALE' if age_ms > 180000 else 'RECENT')
    return {
        'source_exchange': 'bitget', 'symbol': symbol,
        'status': 'SAMPLE_ONLY' if valid else 'NO_SAMPLE',
        'sample_count': valid, 'sample_first_ms': first, 'sample_last_ms': last,
        'sample_age_ms': age_ms, 'sample_freshness': freshness,
        'sample_id_integrity': 'UNVERIFIABLE_IDS' if missing_ids else 'IDS_PRESENT',
        'missing_trade_ids': missing_ids,
        'sample_buy_size': round(buys, 8), 'sample_sell_size': round(sells, 8),
        'sample_net_size': round(buys-sells, 8),
        'coverage_confirmed': False, 'continuous_collection': False,
        'is_cvd': False, 'used_in_trading_score': False,
        'warning': '최근 체결 일부 표본만 조회. 누적 CVD·전체 시장 체결량·승률 아님',
    }


def snapshot(symbol):
    from bitget_market_data import _get
    symbol = _valid_symbol(symbol)
    data = _get('/api/v2/mix/market/fills', {
        'symbol': symbol, 'productType': 'USDT-FUTURES', 'limit': '100'
    })
    return parse_fills(data, symbol)
