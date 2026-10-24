"""BADANG 1.5 supplemental derivatives checks. Public market data only.

CVD is a RECENT TRADE SAMPLE, not full-session CVD. OI is a point-in-time
snapshot, not an OI change rate. Never infer direction from OI or funding alone.
"""
import math
import time
import requests

BASE = 'https://www.okx.com'
TIMEOUT = 7


def number(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError, OverflowError):
        return None


def okx_symbol(symbol):
    if not isinstance(symbol, str) or not symbol.endswith('USDT'):
        return None
    base = symbol[:-4]
    if not base.isalnum() or not base:
        return None
    return base + '-USDT-SWAP'


def fetch(path, params, session=None):
    response = (session or requests).get(BASE + path, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get('code') != '0':
        raise ValueError('OKX API returned non-success')
    return data.get('data') or []


def vwap_from_candles(candles, lookback=48):
    """Typical-price candle VWAP approximation; not tick-exact TradingView VWAP."""
    if not candles or len(candles) < lookback:
        return {'status': 'UNAVAILABLE', 'reason': 'insufficient candles'}
    numerator = denominator = 0.0
    for row in candles[-lookback:]:
        high, low, close, volume = (number(row[i]) for i in (2, 3, 4, 5))
        if any(v is None for v in (high, low, close, volume)) or volume < 0:
            return {'status': 'UNAVAILABLE', 'reason': 'invalid candle'}
        numerator += (high + low + close) / 3 * volume
        denominator += volume
    if denominator <= 0:
        return {'status': 'UNAVAILABLE', 'reason': 'zero volume'}
    vwap = numerator / denominator
    price = number(candles[-1][4])
    return {'status': 'OK', 'value': round(vwap, 10),
            'price_position': 'ABOVE' if price > vwap else 'BELOW' if price < vwap else 'AT',
            'method': '48 closed candles, typical price * base volume / base volume',
            'exact_tick_vwap': False}


def derivatives_snapshot(symbol, session=None):
    inst = okx_symbol(symbol)
    if not inst:
        return {'status': 'UNAVAILABLE', 'reason': 'unsupported symbol'}
    result = {'status': 'PARTIAL', 'exchange': 'okx', 'instrument': inst}
    try:
        rows = fetch('/api/v5/public/open-interest', {'instType': 'SWAP', 'instId': inst}, session)
        row = next((r for r in rows if r.get('instId') == inst), None)
        oi = number(row.get('oi')) if row else None
        result['open_interest'] = {'status': 'OK', 'contracts': oi, 'timestamp': row.get('ts')} if oi is not None else {'status': 'UNAVAILABLE'}
    except (requests.RequestException, ValueError, TypeError) as e:
        result['open_interest'] = {'status': 'UNAVAILABLE', 'reason': type(e).__name__}
    try:
        rows = fetch('/api/v5/public/funding-rate', {'instId': inst}, session)
        row = next((r for r in rows if r.get('instId') == inst), None)
        rate = number(row.get('fundingRate')) if row else None
        result['funding'] = {'status': 'OK', 'predicted_rate': rate, 'funding_time': row.get('fundingTime')} if rate is not None else {'status': 'UNAVAILABLE'}
    except (requests.RequestException, ValueError, TypeError) as e:
        result['funding'] = {'status': 'UNAVAILABLE', 'reason': type(e).__name__}
    try:
        rows = fetch('/api/v5/market/trades', {'instId': inst, 'limit': '500'}, session)
        buy = sell = 0.0
        seen = set()
        for r in rows:
            tid = r.get('tradeId')
            if not tid or tid in seen:
                continue
            seen.add(tid)
            size = number(r.get('sz'))
            if size is None or size <= 0:
                continue
            if r.get('side') == 'buy':
                buy += size
            elif r.get('side') == 'sell':
                sell += size
        total = buy + sell
        if total > 0 and len(seen) >= 40:
            result['cvd'] = {'status': 'OK', 'sample_contract_delta': round(buy - sell, 6),
                             'taker_imbalance': round((buy - sell) / total, 5),
                             'trade_count': len(seen),
                             'method': 'most recent <=500 public trades, contract-size units; NOT full candle/session CVD'}
        else:
            result['cvd'] = {'status': 'UNAVAILABLE', 'reason': 'insufficient sampled trades'}
    except (requests.RequestException, ValueError, TypeError) as e:
        result['cvd'] = {'status': 'UNAVAILABLE', 'reason': type(e).__name__}
    result['status'] = 'OK' if all(result[k]['status'] == 'OK' for k in ('open_interest', 'funding', 'cvd')) else 'PARTIAL'
    result['observed_at_ms'] = int(time.time() * 1000)
    return result


def evaluate_high_confidence(item, candles, snapshot=None):
    """Independent research flag; never mutates legacy recommendation or score."""
    direction = item.get('recommendation')
    vwap = vwap_from_candles(candles)
    snapshot = snapshot or {'status': 'UNAVAILABLE'}
    checks = {'legacy_recommendation': direction in ('LONG', 'SHORT'),
              'trend_aligned': item.get('trend_aligned') is True,
              'vwap_confirmed': False,
              'cvd_confirmed': False,
              'oi_available': snapshot.get('open_interest', {}).get('status') == 'OK',
              'funding_available': snapshot.get('funding', {}).get('status') == 'OK'}
    if direction in ('LONG', 'SHORT') and vwap.get('status') == 'OK':
        checks['vwap_confirmed'] = vwap['price_position'] == ('ABOVE' if direction == 'LONG' else 'BELOW')
    cvd = snapshot.get('cvd', {})
    imbalance = number(cvd.get('taker_imbalance'))
    if direction in ('LONG', 'SHORT') and cvd.get('status') == 'OK' and imbalance is not None:
        checks['cvd_confirmed'] = imbalance >= 0.12 if direction == 'LONG' else imbalance <= -0.12
    # No 'high confidence' claim from a short trade sample or single OI snapshot.
    return {'status': 'RESEARCH_ONLY', 'eligible_for_alert': False,
            'checks': checks, 'vwap': vwap, 'derivatives': snapshot,
            'reason': '실제 성과 검증 전: 자동 알림 미승인. OI 변화 이력과 연속 CVD 수집 필요'}
