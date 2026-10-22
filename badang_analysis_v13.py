"""BADANG Trading 1.3 — technical analysis engine.

Divergence, Elliott wave and trendline analysis.
Use confirmed OHLCV candles.
"""
from __future__ import annotations

from statistics import mean
from typing import Any
import math


def _num(v: Any) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else float('nan')
    except (TypeError, ValueError):
        return float('nan')


def normalize(candles: list) -> list[dict]:
    out = []
    for c in candles:
        if isinstance(c, dict):
            d = {
                k: _num(c.get(k))
                for k in ('open', 'high', 'low', 'close', 'volume')
            }
        else:
            if len(c) < 6:
                continue
            d = dict(zip(
                ('open', 'high', 'low', 'close', 'volume'),
                map(_num, c[1:6])
            ))

        if not all(math.isfinite(v) for v in d.values()):
            continue

        if (
            d['low'] <= 0
            or d['high'] < max(d['open'], d['close'], d['low'])
            or d['low'] > min(d['open'], d['close'])
            or d['volume'] < 0
        ):
            continue

        out.append(d)
    return out


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []

    k = 2 / (period + 1)
    result = [values[0]]

    for x in values[1:]:
        result.append(x * k + result[-1] * (1 - k))

    return result


def rsi(values: list[float], period: int = 14) -> list:
    result = [None] * len(values)

    if len(values) <= period:
        return result

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = sum(max(v, 0) for v in changes[:period]) / period
    losses = sum(max(-v, 0) for v in changes[:period]) / period

    def calc(g, l):
        if l == 0 and g > 0:
            return 100
        if l == 0:
            return 50
        return 100 - 100 / (1 + g / l)

    result[period] = calc(gains, losses)

    for i in range(period + 1, len(values)):
        change = changes[i - 1]

        gains = (
            gains * (period - 1) + max(change, 0)
        ) / period

        losses = (
            losses * (period - 1) + max(-change, 0)
        ) / period

        result[i] = calc(gains, losses)

    return result


def atr(rows: list[dict], period: int = 14) -> float:
    tr = []

    for i in range(1, len(rows)):
        r = rows[i]
        prev = rows[i - 1]

        tr.append(max(
            r['high'] - r['low'],
            abs(r['high'] - prev['close']),
            abs(r['low'] - prev['close'])
        ))

    return mean(tr[-period:]) if len(tr) >= period else 0.0


def pivots(
    rows: list[dict],
    radius: int = 3
) -> list[tuple[int, str, float]]:
    points = []

    for i in range(radius, len(rows) - radius):
        segment = rows[i-radius:i+radius+1]

        if rows[i]['high'] == max(r['high'] for r in segment):
            points.append((i, 'H', rows[i]['high']))

        if rows[i]['low'] == min(r['low'] for r in segment):
            points.append((i, 'L', rows[i]['low']))

    result = []

    for p in points:
        if result and result[-1][1] == p[1]:
            if (
                (p[1] == 'H' and p[2] > result[-1][2])
                or (p[1] == 'L' and p[2] < result[-1][2])
            ):
                result[-1] = p
        else:
            result.append(p)

    return result


def divergence_details(
    points, rsi_series, total_bars, max_age=18
):
    """Find recent regular and hidden RSI divergences."""
    found = []

    for typ in ('L', 'H'):
        relevant = [
            p for p in points
            if p[1] == typ and rsi_series[p[0]] is not None
        ]

        for a, b in zip(relevant[-5:-1], relevant[-4:]):
            age = total_bars - 1 - b[0]
            separation = b[0] - a[0]

            if age > max_age or not 5 <= separation <= 65:
                continue

            pa, pb = a[2], b[2]
            ra, rb = rsi_series[a[0]], rsi_series[b[0]]

            price_delta_pct = (
                (pb - pa) / pa * 100 if pa else 0
            )
            rsi_delta = rb - ra

            if (
                abs(price_delta_pct) < 0.12
                or abs(rsi_delta) < 3
            ):
                continue

            kind = None

            if typ == 'L':
                if price_delta_pct < 0 and rsi_delta > 0:
                    kind = 'bullish'
                elif price_delta_pct > 0 and rsi_delta < 0:
                    kind = 'hidden_bullish'
            else:
                if price_delta_pct > 0 and rsi_delta < 0:
                    kind = 'bearish'
                elif price_delta_pct < 0 and rsi_delta > 0:
                    kind = 'hidden_bearish'

            if kind:
                found.append({
                    'type': kind,
                    'age_bars': age,
                    'first_pivot_index': a[0],
                    'second_pivot_index': b[0],
                    'price_change_pct': round(price_delta_pct, 3),
                    'rsi_change': round(rsi_delta, 2),
                    'confirmed': True
                })

    newest = {}

    for item in found:
        kind = item['type']

        if (
            kind not in newest
            or item['age_bars'] < newest[kind]['age_bars']
        ):
            newest[kind] = item

    return sorted(
        newest.values(),
        key=lambda x: x['age_bars']
    )


def divergence(points, rsi_series):
    details = divergence_details(
        points, rsi_series, len(rsi_series)
    )

    return [
        d['type'] for d in details
        if d['type'] in ('bullish', 'bearish')
    ]


def wave_candidates(points):
    """Elliott wave candidates, not confirmed wave counts."""
    recent = points[-12:]
    patterns = []

    def add(
        pattern, direction, confidence,
        reasons, invalidation=None, ratios=None
    ):
        patterns.append({
            'pattern': pattern,
            'direction': direction,
            'confidence': confidence,
            'reasons': reasons,
            'invalidation_price': invalidation,
            'ratios': ratios or {}
        })

    if len(recent) >= 4:
        p = recent[-4:]

        a, b, c = [
            p[i + 1][2] - p[i][2]
            for i in range(3)
        ]

        if a * b < 0 and b * c < 0 and abs(a) > 0:
            b_ratio = abs(b / a)
            c_ratio = abs(c / a)

            if (
                0.236 <= b_ratio <= 0.886
                and 0.618 <= c_ratio <= 1.618
            ):
                add(
                    'ABC correction candidate',
                    'up' if c > 0 else 'down',
                    (
                        'medium'
                        if 0.382 <= b_ratio <= 0.786
                        else 'low'
                    ),
                    [
                        'Alternating A-B-C swings',
                        'B retracement within plausible range',
                        'C length within Fibonacci range'
                    ],
                    p[2][2],
                    {
                        'b_to_a': round(b_ratio, 3),
                        'c_to_a': round(c_ratio, 3)
                    }
                )

    if len(recent) >= 6:
        p = recent[-6:]
        prices = [x[2] for x in p]

        moves = [
            prices[i + 1] - prices[i]
            for i in range(5)
        ]

        direction = 1 if moves[0] > 0 else -1

        alternating = (
            all(
                moves[i] * direction > 0
                for i in (0, 2, 4)
            )
            and all(
                moves[i] * direction < 0
                for i in (1, 3)
            )
        )

        if alternating:
            w1, w2, w3, w4, w5 = [
                abs(x) for x in moves
            ]

            rule_2 = (
                (prices[2] - prices[0]) * direction > 0
            )
            rule_3 = w3 >= min(w1, w5)
            rule_4 = (
                (prices[4] - prices[1]) * direction > 0
            )

            ratio_2 = w2 / w1 if w1 else 0
            ratio_4 = w4 / w3 if w3 else 0
            ratio_3 = w3 / w1 if w1 else 0

            if rule_2 and rule_3 and rule_4:
                fib_support = (
                    0.236 <= ratio_2 <= 0.886
                    and 0.146 <= ratio_4 <= 0.618
                )

                add(
                    '5-wave impulse candidate',
                    'up' if direction > 0 else 'down',
                    'medium' if fib_support else 'low',
                    [
                        'Wave 2 does not exceed wave 1 origin',
                        'Wave 3 is not the shortest motive wave',
                        'Wave 4 does not overlap wave 1 territory',
                        'Fibonacci retracements checked'
                    ],
                    prices[4],
                    {
                        'wave2_retracement': round(
                            ratio_2, 3
                        ),
                        'wave3_extension': round(
                            ratio_3, 3
                        ),
                        'wave4_retracement': round(
                            ratio_4, 3
                        )
                    }
                )

   return patterns
def trendline_analysis(
    rows: list[dict],
    points: list,
    atr_value: float,
    volume_ratio: float,
    lookback: int = 90
) -> dict:
    """Detect trendline breaks from confirmed swing pivots."""
    n = len(rows)

    result = {
        'support': None,
        'resistance': None,
        'events': [],
        'signal': 'NONE',
        'warning': False
    }

    if n < 30 or atr_value <= 0:
        return result

    buffer = 0.15 * atr_value
    cutoff = max(0, n - lookback)

    definitions = (
        ('support', 'L'),
        ('resistance', 'H')
    )

    for name, kind in definitions:
        swings = [
            p for p in points
            if p[1] == kind and p[0] >= cutoff
        ]

        if len(swings) < 2:
            continue

        a, b = swings[-2:]

        if b[0] <= a[0]:
            continue

        slope = (
            (b[2] - a[2]) / (b[0] - a[0])
        )

        if name == 'support' and slope <= 0:
            continue

        if name == 'resistance' and slope >= 0:
            continue

        prev_level = (
            b[2] + slope * (n - 2 - b[0])
        )

        level = (
            b[2] + slope * (n - 1 - b[0])
        )

        if level <= 0 or prev_level <= 0:
            continue

        if abs(slope) > 1.5 * atr_value:
            continue

        info = {
            'first_pivot_index': a[0],
            'second_pivot_index': b[0],
            'first_pivot_price': a[2],
            'second_pivot_price': b[2],
            'slope_per_bar': slope,
            'current_level': level,
            'previous_level': prev_level,
            'touches': 2
        }

        result[name] = info

        prev_close = rows[-2]['close']
        close = rows[-1]['close']

        if name == 'resistance':
            crossed = (
                prev_close <= prev_level + buffer
                and close > level + buffer
            )

            event = 'BREAKOUT_UP'
            direction = 'LONG'

            fake = (
                close <= level + buffer
                and rows[-1]['high'] > level + buffer
            )

        else:
            crossed = (
                prev_close >= prev_level - buffer
                and close < level - buffer
            )

            event = 'BREAKDOWN_DOWN'
            direction = 'SHORT'

            fake = (
                close >= level - buffer
                and rows[-1]['low'] < level - buffer
            )

        if fake:
            result['events'].append({
                'type': 'POSSIBLE_FALSE_BREAK',
                'line': name,
                'level': level,
                'volume_ratio': volume_ratio
            })

        if crossed:
            confirmed_volume = volume_ratio >= 1.2

            result['events'].append({
                'type': event,
                'line': name,
                'direction': direction,
                'level': level,
                'volume_ratio': volume_ratio,
                'volume_confirmed': confirmed_volume
            })

            if confirmed_volume:
                result['signal'] = event
            else:
                result['warning'] = True

    return result


def analyze(
    candles: list,
    mode: str = 'scalp',
    funding_rate=None,
    oi_change_pct=None,
    symbol: str = ''
) -> dict:
    rows = normalize(candles)

    if len(rows) < 205:
        return {
            'symbol': symbol,
            'status': 'insufficient_data',
            'count': len(rows),
            'recommendation': 'WAIT'
        }

    close = [r['close'] for r in rows]

    e20, e50, e200 = (
        ema(close, n)[-1]
        for n in (20, 50, 200)
    )

    rs = rsi(close)

    macd = [
        a - b
        for a, b in zip(
            ema(close, 12),
            ema(close, 26)
        )
    ]

    signal = ema(macd, 9)
    hist = macd[-1] - signal[-1]
    prev_hist = macd[-2] - signal[-2]
    p = close[-1]

    points = pivots(rows)

    div_details = divergence_details(
        points, rs, len(rows)
    )

    div = [d['type'] for d in div_details]

    vol_avg = mean(
        r['volume'] for r in rows[-21:-1]
    )

    vol_ratio = (
        rows[-1]['volume'] / vol_avg
        if vol_avg > 0 else 0
    )

    volatility = atr(rows)

    trendlines = trendline_analysis(
        rows, points, volatility, vol_ratio
    )

    highs = [
        x[2] for x in points if x[1] == 'H'
    ]

    lows = [
        x[2] for x in points if x[1] == 'L'
    ]

    recent_hi = max(
        r['high'] for r in rows[-60:]
    )

    recent_lo = min(
        r['low'] for r in rows[-60:]
    )

    span = recent_hi - recent_lo

    fib = {
        'retracement_382':
            recent_hi - 0.382 * span,
        'retracement_500':
            recent_hi - 0.5 * span,
        'retracement_618':
            recent_hi - 0.618 * span,
        'extension_1272_up':
            recent_hi + 0.272 * span,
        'extension_1272_down':
            recent_lo - 0.272 * span
    }

    long_score = 50
    short_score = 50

    reasons_long = []
    reasons_short = []

    def score(side, points, reason):
        nonlocal long_score, short_score

        if side == 'long':
            long_score += points
            reasons_long.append(reason)
        else:
            short_score += points
            reasons_short.append(reason)

    if p > e20 > e50 > e200:
        score(
            'long', 18,
            'EMA bullish alignment'
        )

    if p < e20 < e50 < e200:
        score(
            'short', 18,
            'EMA bearish alignment'
        )

    if e20 > e50:
        score(
            'long', 8,
            'EMA20 above EMA50'
        )

    elif e20 < e50:
        score(
            'short', 8,
            'EMA20 below EMA50'
        )

    if hist > 0 and hist > prev_hist:
        score(
            'long', 12,
            'MACD histogram rising positive'
        )

    if hist < 0 and hist < prev_hist:
        score(
            'short', 12,
            'MACD histogram falling negative'
        )

    if rs[-1] is not None:
        if 50 < rs[-1] < 72:
            score(
                'long', 8,
                'RSI bullish range'
            )

        if 28 < rs[-1] < 50:
            score(
                'short', 8,
                'RSI bearish range'
            )

    if 'bullish' in div:
        score(
            'long', 12,
            'bullish RSI divergence candidate'
        )

    if 'bearish' in div:
        score(
            'short', 12,
            'bearish RSI divergence candidate'
        )

    if (
        'hidden_bullish' in div
        and e20 > e50
    ):
        score(
            'long', 8,
            'hidden bullish RSI divergence candidate'
        )

    if (
        'hidden_bearish' in div
        and e20 < e50
    ):
        score(
            'short', 8,
            'hidden bearish RSI divergence candidate'
        )

    if vol_ratio >= 1.5:
        if close[-1] > close[-2]:
            score(
                'long', 8,
                'rising volume with green candle'
            )

        elif close[-1] < close[-2]:
            score(
                'short', 8,
                'rising volume with red candle'
            )

    if trendlines['signal'] == 'BREAKOUT_UP':
        score(
            'long', 12,
            'confirmed downward trendline breakout'
        )

    elif trendlines['signal'] == 'BREAKDOWN_DOWN':
        score(
            'short', 12,
            'confirmed upward trendline breakdown'
        )

    f = (
        _num(funding_rate)
        if funding_rate is not None
        else None
    )

    oi = (
        _num(oi_change_pct)
        if oi_change_pct is not None
        else None
    )

    if f is not None and math.isfinite(f):
        if f > 0.0005:
            score(
                'short', 4,
                'high positive funding: crowded longs'
            )

        elif f < -0.0005:
            score(
                'long', 4,
                'negative funding: crowded shorts'
            )

    if (
        oi is not None
        and math.isfinite(oi)
        and oi > 3
    ):
        if close[-1] > close[-2]:
            score(
                'long', 5,
                'OI rising with price'
            )

        elif close[-1] < close[-2]:
            score(
                'short', 5,
                'OI rising while price falls'
            )

    long_score = min(100, long_score)
    short_score = min(100, short_score)

    side = (
        'LONG'
        if long_score > short_score
        else 'SHORT'
    )

    best = max(long_score, short_score)

    direction = 1 if side == 'LONG' else -1

    recent_low = (
        min(lows[-3:])
        if lows else
        min(r['low'] for r in rows[-20:])
    )

    recent_high = (
        max(highs[-3:])
        if highs else
        max(r['high'] for r in rows[-20:])
    )

    stop = (
        min(recent_low, p - 1.5 * volatility)
        if direction == 1
        else max(
            recent_high,
            p + 1.5 * volatility
        )
    )

    risk = abs(p - stop)

    target1 = p + direction * 1.5 * risk
    target2 = p + direction * 2.0 * risk

    rr = (
        abs(target1 - p) / risk
        if risk > 0
        else 0
    )

    opposite_divergence = (
        any(
            d in div
            for d in (
                'bearish',
                'hidden_bearish'
            )
        )
        if side == 'LONG'
        else any(
            d in div
            for d in (
                'bullish',
                'hidden_bullish'
            )
        )
    )

    opposite_trendline = (
        trendlines['signal'] == 'BREAKDOWN_DOWN'
        if side == 'LONG'
        else trendlines['signal'] == 'BREAKOUT_UP'
    )

    recommended = (
        best >= 80
        and rr >= 1.5
        and volatility > 0
        and len(
            reasons_long
            if side == 'LONG'
            else reasons_short
        ) >= 3
        and not opposite_divergence
        and not opposite_trendline
    )

    return {
        'symbol': symbol,
        'status': 'ok',
        'mode': mode,
        'recommendation':
            side if recommended else 'WAIT',
        'candidate_side': side,
        'long_score': long_score,
        'short_score': short_score,
        'entry_reference': p,
        'stop_loss': stop,
        'take_profit_1': target1,
        'take_profit_2': target2,
        'risk_reward_1': round(rr, 2),
        'rsi': round(rs[-1], 2),
        'macd_histogram': hist,
        'ema20': e20,
        'ema50': e50,
        'ema200': e200,
        'volume_ratio': round(vol_ratio, 2),
        'atr14': volatility,
        'divergences': div,
        'divergence_details': div_details,
        'divergence_warning':
            opposite_divergence,
        'trendlines': trendlines,
        'trendline_warning':
            opposite_trendline,
        'wave_candidates':
            wave_candidates(points),
        'fibonacci': fib,
        'funding_rate': f,
        'oi_change_pct': oi,
        'futures_data_available': {
            'funding':
                f is not None
                and math.isfinite(f),
            'oi':
                oi is not None
                and math.isfinite(oi)
        },
        'reasons':
            reasons_long
            if side == 'LONG'
            else reasons_short,
        'caveats': [
            'Confirm higher timeframe before acting',
            'Wave labels are unconfirmed candidates',
            'Targets exclude fees and slippage',
            'Divergences can fail without reversal',
            'Trendline breaks require backtesting'
        ]
    }


def top_five(
    analyses: list[dict]
) -> list[dict]:
    eligible = [
        a for a in analyses
        if (
            a.get('recommendation')
            in ('LONG', 'SHORT')
            and a.get('status') == 'ok'
        )
    ]

    return sorted(
        eligible,
        key=lambda a: max(
            a['long_score'],
            a['short_score']
        ),
        reverse=True
    )[:5]
