import os
import re
import time
import math
import json
import logging
import requests
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, render_template, render_template_string, request

app = Flask(__name__)

# BADANG 1.7.2: standalone read-only dashboard route
from badang_dashboard import badang_dashboard
app.register_blueprint(badang_dashboard)
BASE = 'https://api.bitget.com'
S = requests.Session()
API_LOCK = threading.Lock()
LAST_API_CALL = [0.0]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('badang')

# ============================================================
# BADANG Trading 1.4
# PostgreSQL recommendation signal history
# Existing 1.3 endpoints and analysis preserved
# ============================================================

DB_INIT_LOCK = threading.Lock()
DB_INITIALIZED = False

CREATE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS badang_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(40) NOT NULL,
    mode VARCHAR(12) NOT NULL,
    direction VARCHAR(8) NOT NULL,
    score INTEGER NOT NULL,
    exchange VARCHAR(30),
    reference_time BIGINT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entry_price DOUBLE PRECISION NOT NULL,
    stop_price DOUBLE PRECISION NOT NULL,
    tp1_price DOUBLE PRECISION NOT NULL,
    tp2_price DOUBLE PRECISION,
    risk_reward DOUBLE PRECISION,
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    analysis_json JSONB,
    CONSTRAINT badang_signals_unique
        UNIQUE (symbol, mode, direction, reference_time)
)
"""


def database_url():
    url = os.environ.get('DATABASE_URL', '').strip()
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


def db_connect():
    url = database_url()
    if not url:
        raise RuntimeError('DATABASE_URL 환경변수가 설정되지 않았습니다.')

    import psycopg2
    return psycopg2.connect(
        url,
        connect_timeout=5,
        application_name='badang-trading-v14'
    )


def ensure_database():
    global DB_INITIALIZED

    if DB_INITIALIZED:
        return

    with DB_INIT_LOCK:
        if DB_INITIALIZED:
            return

        conn = db_connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(CREATE_SIGNALS_TABLE)
            DB_INITIALIZED = True
        finally:
            conn.close()


def finite_number(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def first_number(data, keys):
    if not isinstance(data, dict):
        return None

    for key in keys:
        number = finite_number(data.get(key))
        if number is not None:
            return number

    return None


def first_dict(data, keys):
    if not isinstance(data, dict):
        return {}

    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value

    return {}


def get_reference_time(item, candles_data=None):
    """
    Prefer last confirmed candle timestamp.
    No fabricated reference timestamp is allowed.
    """
    if candles_data:
        try:
            return int(float(candles_data[-1][0]))
        except (IndexError, ValueError, TypeError):
            pass

    for source in (
        item,
        item.get('setup', {}) if isinstance(item, dict) else {}
    ):
        if not isinstance(source, dict):
            continue

        for key in (
            'last_closed',
            'last_closed_time',
            'candle_time',
            'timestamp'
        ):
            value = finite_number(source.get(key))
            if value is not None and value > 0:
                return int(value)

    return None


def extract_v13_signal(item, mode, candles_data=None):
    """
    Return a validated signal or None.

    Records only the final recommendation, never candidate_side
    alone. Missing price fields are not guessed.
    """
    if not isinstance(item, dict):
        return None

    direction = item.get('recommendation')
    if direction not in ('LONG', 'SHORT'):
        return None

    if item.get('trend_aligned') is False:
        return None

    symbol = str(item.get('symbol', '')).upper().strip()
    if not symbol or len(symbol) > 40:
        return None

    score_key = (
        'long_score' if direction == 'LONG'
        else 'short_score'
    )
    score = finite_number(item.get(score_key))
    if score is None or not 0 <= score <= 100:
        return None

    plan = first_dict(
        item,
        ('plan', 'trade_plan', 'scenario', 'trade_setup')
    )

    entry_keys = (
        'entry_reference', 'entry_price',
        'entry', 'suggested_entry'
    )
    stop_keys = (
        'stop_loss', 'stop_price',
        'stop', 'sl'
    )
    tp1_keys = (
        'take_profit_1', 'take_profit1',
        'tp1', 'target_1', 'target1'
    )
    tp2_keys = (
        'take_profit_2', 'take_profit2',
        'tp2', 'target_2', 'target2'
    )

    entry = first_number(item, entry_keys)
    stop = first_number(item, stop_keys)
    tp1 = first_number(item, tp1_keys)
    tp2 = first_number(item, tp2_keys)

    if entry is None:
        entry = first_number(plan, entry_keys)
    if stop is None:
        stop = first_number(plan, stop_keys)
    if tp1 is None:
        tp1 = first_number(plan, tp1_keys)
    if tp2 is None:
        tp2 = first_number(plan, tp2_keys)

    if None in (entry, stop, tp1):
        return None

    if min(entry, stop, tp1) <= 0:
        return None

    if direction == 'LONG':
        valid_prices = stop < entry < tp1
        if tp2 is not None and tp2 <= entry:
            tp2 = None
    else:
        valid_prices = tp1 < entry < stop
        if tp2 is not None and tp2 >= entry:
            tp2 = None

    if not valid_prices:
        return None

    risk = abs(entry - stop)
    if risk <= 0:
        return None

    rr = abs(tp1 - entry) / risk
    reference_time = get_reference_time(item, candles_data)
    if reference_time is None:
        return None

    # Normalize seconds to milliseconds when necessary.
    if reference_time < 100000000000:
        reference_time *= 1000

    if reference_time <= 0:
        return None

    return {
        'symbol': symbol,
        'mode': mode,
        'direction': direction,
        'score': int(round(score)),
        'exchange': str(item.get('exchange') or ''),
        'reference_time': reference_time,
        'entry_price': entry,
        'stop_price': stop,
        'tp1_price': tp1,
        'tp2_price': tp2,
        'risk_reward': round(rr, 4),
        'analysis_json': json.dumps(
            item, ensure_ascii=False, default=str
        )
    }


def save_signals(signals):
    """
    Best-effort persistence.
    Database errors must never break the market scanner.
    """
    if not signals:
        return {
            'saved': 0,
            'duplicates': 0,
            'skipped': 0,
            'storage': 'no_eligible_signals'
        }

    if not database_url():
        return {
            'saved': 0,
            'duplicates': 0,
            'skipped': len(signals),
            'storage': 'not_configured'
        }

    try:
        ensure_database()

        conn = db_connect()
        saved = 0

        try:
            with conn:
                with conn.cursor() as cur:
                    for signal in signals:
                        cur.execute(
                            """
                            INSERT INTO badang_signals (
                                symbol, mode, direction, score,
                                exchange, reference_time,
                                entry_price, stop_price,
                                tp1_price, tp2_price,
                                risk_reward, analysis_json
                            )
                            VALUES (
                                %s, %s, %s, %s,
                                %s, %s,
                                %s, %s,
                                %s, %s,
                                %s, %s::jsonb
                            )
                            ON CONFLICT (
                                symbol, mode, direction,
                                reference_time
                            )
                            DO NOTHING
                            RETURNING id
                            """,
                            (
                                signal['symbol'],
                                signal['mode'],
                                signal['direction'],
                                signal['score'],
                                signal['exchange'],
                                signal['reference_time'],
                                signal['entry_price'],
                                signal['stop_price'],
                                signal['tp1_price'],
                                signal['tp2_price'],
                                signal['risk_reward'],
                                signal['analysis_json']
                            )
                        )
                        if cur.fetchone() is not None:
                            saved += 1

            return {
                'saved': saved,
                'duplicates': len(signals) - saved,
                'skipped': 0,
                'storage': 'connected'
            }
        finally:
            conn.close()

    except Exception as exc:
        logger.exception('Signal storage failed: %s', exc)
        return {
            'saved': 0,
            'duplicates': 0,
            'skipped': len(signals),
            'storage': 'error'
        }


def record_v13_results(results, mode, candle_map):
    signals = []

    for item in results:
        try:
            symbol = item.get('symbol', '')
            rows = candle_map.get(symbol)
            signal = extract_v13_signal(item, mode, rows)
            if signal is not None:
                signals.append(signal)
        except Exception:
            logger.exception('Signal extraction failed')

    return save_signals(signals)


# ============================================================
# Original Bitget API functions
# ============================================================

def api(path, params=None):
    for attempt in range(5):
        with API_LOCK:
            elapsed = time.monotonic() - LAST_API_CALL[0]
            if elapsed < 0.4:
                time.sleep(0.4 - elapsed)

            LAST_API_CALL[0] = time.monotonic()

            try:
                r = S.get(
                    BASE + path,
                    params=params,
                    timeout=15
                )

                if r.status_code == 429:
                    retry = True
                else:
                    r.raise_for_status()
                    j = r.json()

                    if j.get('code') == '00000':
                        return j.get('data', [])

                    if str(j.get('code')) in (
                        '429', '40015', '40017'
                    ):
                        retry = True
                    else:
                        raise ValueError(
                            str(j.get('msg', 'API error'))
                        )

            except requests.exceptions.RequestException:
                if attempt == 4:
                    raise
                retry = True

        if retry and attempt < 4:
            time.sleep(min(2 * (attempt + 1), 8))

    raise ValueError(
        'Bitget API 요청 제한 또는 일시적 통신 오류'
    )


def ema(a, n):
    v = a[0]
    out = []
    k = 2 / (n + 1)

    for x in a:
        v = x * k + v * (1 - k)
        out.append(v)

    return out


def rsi(a, n=14):
    gains = []
    losses = []

    for i in range(1, len(a)):
        d = a[i] - a[i - 1]
        gains.append(max(0, d))
        losses.append(max(0, -d))

    g = sum(gains[:n]) / n
    l = sum(losses[:n]) / n

    for i in range(n, len(gains)):
        g = (g * (n - 1) + gains[i]) / n
        l = (l * (n - 1) + losses[i]) / n

    return 100 if l == 0 else 100 - 100 / (1 + g / l)


def pivots(a, low=True, w=3):
    return [
        i for i in range(w, len(a) - w)
        if a[i] == (
            min if low else max
        )(a[i-w:i+w+1])
    ]


def divergence(close, rsis):
    for low in (True, False):
        ps = pivots(close, low)

        if len(ps) < 2:
            continue

        i, j = ps[-2:]

        if j - i > 40:
            continue

        if (
            low
            and close[j] < close[i]
            and rsis[j] > rsis[i] + 2
        ):
            return 'bullish'

        if (
            not low
            and close[j] > close[i]
            and rsis[j] < rsis[i] - 2
        ):
            return 'bearish'

    return 'none'


def candles(symbol, gran):
    from exchange_data import fastest_candles

    result = fastest_candles(
        symbol,
        gran,
        exchanges=['bitget', 'okx']
    )
    return result['candles']


def analyze(symbol, gran):
    rows = candles(symbol, gran)

    c = [float(x[4]) for x in rows]
    h = [float(x[2]) for x in rows]
    l = [float(x[3]) for x in rows]
    v = [float(x[5]) for x in rows]

    e20 = ema(c, 20)
    e50 = ema(c, 50)
    e200 = ema(c, 200)

    rs = [50.0] * 15

    for k in range(16, len(c) + 1):
        rs.append(rsi(c[:k]))

    rs = rs[:len(c)]

    mac = [
        a - b
        for a, b in zip(ema(c, 12), ema(c, 26))
    ]
    sig = ema(mac, 9)

    vol = sum(v[-21:-1]) / 20
    ratio = v[-1] / vol if vol else 0

    prev_hi = max(h[-21:-1])
    prev_lo = min(l[-21:-1])
    price = c[-1]

    bull = (
        e20[-1] > e50[-1] > e200[-1]
        and mac[-1] > sig[-1]
        and 48 <= rs[-1] <= 72
    )

    bear = (
        e20[-1] < e50[-1] < e200[-1]
        and mac[-1] < sig[-1]
        and 28 <= rs[-1] <= 52
    )

    div = divergence(c, rs)

    br_up = price > prev_hi and ratio >= 1.2
    br_down = price < prev_lo and ratio >= 1.2

    rng = max(h[-1] - l[-1], 1e-12)
    pos = (price - l[-1]) / rng

    fake_up = br_up and pos < 0.65
    fake_down = br_down and pos > 0.35

    direction = (
        'LONG' if bull
        else 'SHORT' if bear
        else 'WAIT'
    )

    if (
        (direction == 'LONG' and fake_up)
        or (direction == 'SHORT' and fake_down)
    ):
        direction = 'WAIT'

    if (
        (direction == 'LONG' and div == 'bearish')
        or (direction == 'SHORT' and div == 'bullish')
    ):
        direction = 'WAIT'

    trs = [
        max(
            h[i] - l[i],
            abs(h[i] - c[i-1]),
            abs(l[i] - c[i-1])
        )
        for i in range(1, len(c))
    ]

    atr = sum(trs[-14:]) / 14

    stop = (
        min(l[-11:-1]) - 0.2 * atr
        if direction == 'LONG'
        else max(h[-11:-1]) + 0.2 * atr
        if direction == 'SHORT'
        else None
    )

    risk = abs(price - stop) if stop is not None else 0

    target = (
        price + 2 * risk
        if direction == 'LONG'
        else price - 2 * risk
        if direction == 'SHORT'
        else None
    )

    if risk <= 0 or (
        target is not None and target <= 0
    ):
        direction = 'WAIT'
        stop = None
        target = None

    return {
        'rows': rows,
        'symbol': symbol,
        'timeframe': gran,
        'price': price,
        'rsi': round(rs[-1], 1),
        'volume_ratio': round(ratio, 2),
        'divergence': div,
        'trend': (
            'UP'
            if e20[-1] > e50[-1] > e200[-1]
            else 'DOWN'
            if e20[-1] < e50[-1] < e200[-1]
            else 'MIXED'
        ),
        'breakout': (
            'UP' if br_up
            else 'DOWN' if br_down
            else 'NONE'
        ),
        'fake_breakout': fake_up or fake_down,
        'direction': direction,
        'stop': stop,
        'target': target,
        'support': prev_lo,
        'resistance': prev_hi,
        'last_closed': int(rows[-1][0]),
        'atr': atr,
        'swing_low': min(l[-11:-1]),
        'swing_high': max(h[-11:-1]),
        'reason': (
            '확정봉 EMA20/50/200, MACD, RSI, '
            '거래량 및 돌파 검증'
        )
    }


def symbols(min_turnover):
    data = api(
        '/api/v2/mix/market/tickers',
        {'productType': 'USDT-FUTURES'}
    )

    out = []

    for x in data:
        try:
            sym = x['symbol']
            turn = float(x.get('usdtVolume', 0))

            if (
                sym.endswith('USDT')
                and turn >= min_turnover
            ):
                out.append((sym, turn))

        except (ValueError, KeyError, TypeError):
            pass

    return sorted(
        out,
        key=lambda z: z[1],
        reverse=True
    )


def flow_analysis(symbol, frame, setup):
    """
    Candle-based proxy, not true trade-side CVD
    or net capital flow.
    """
    rows = setup['rows']

    cl = [float(r[4]) for r in rows]
    op = [float(r[1]) for r in rows]

    turnover = [
        float(r[6])
        if len(r) > 6
        else float(r[5]) * cl[i]
        for i, r in enumerate(rows)
    ]

    signed = [
        (
            1 if cl[i] > op[i]
            else -1 if cl[i] < op[i]
            else 0
        ) * turnover[i]
        for i in range(len(rows))
    ]

    recent = sum(signed[-5:])
    prior = sum(signed[-10:-5])
    volume = sum(turnover[-5:])
    baseline = sum(turnover[-25:-5]) / 4

    strength = volume / baseline if baseline > 0 else 0
    pressure = recent / max(volume, 1e-12)

    if strength >= 1.1 and pressure >= 0.16:
        state = 'BUY'
    elif strength >= 1.1 and pressure <= -0.16:
        state = 'SELL'
    else:
        state = 'NEUTRAL'

    return {
        'state': state,
        'pressure': round(pressure * 100, 1),
        'turnover_ratio': round(strength, 2),
        'delta_proxy': round(recent, 2),
        'delta_change': round(recent - prior, 2),
        'method': (
            '양봉/음봉 거래대금 기반 추정치 '
            '(실제 CVD·순자금 유입 아님)'
        ),
        'oi': 'UNAVAILABLE',
        'funding': 'UNAVAILABLE'
    }


def score_direction(
    setup, higher, flow, direction, lower
):
    up = direction == 'LONG'
    trend = 'UP' if up else 'DOWN'
    opposite = 'bearish' if up else 'bullish'

    score = 0

    score += (
        25 if setup['trend'] == trend else 0
    )
    score += (
        20 if higher == trend else 0
    )
    score += (
        15 if (
            setup['rsi'] >= 52
            if up else setup['rsi'] <= 48
        ) else 0
    )
    score += (
        15 if (
            flow['state'] == 'BUY'
            if up else flow['state'] == 'SELL'
        ) else 0
    )
    score += (
        10 if setup['volume_ratio'] >= 1.1 else 0
    )
    score += (
        10 if lower['divergence'] == (
            'bullish' if up else 'bearish'
        ) else 0
    )
    score += (
        5 if (
            not setup['fake_breakout']
            and setup['divergence'] != opposite
        ) else 0
    )

    return score


def scenario(setup, direction, mode):
    price = setup['price']
    atr = setup['atr']
    up = direction == 'LONG'

    if price <= 0 or atr <= 0:
        return None

    entry = price

    stop = (
        min(
            setup['swing_low'],
            entry - 1.2 * atr
        )
        if up
        else max(
            setup['swing_high'],
            entry + 1.2 * atr
        )
    )

    risk = (
        entry - stop
        if up else stop - entry
    )

    if risk <= 0 or risk / entry > 0.2:
        return None

    minimum = 1.5 if mode == 'scalp' else 2.0

    tp1 = (
        entry + (risk if up else -risk) * minimum
    )
    tp2 = (
        entry + (risk if up else -risk) * (minimum + 1)
    )

    if min(stop, tp1, tp2) <= 0:
        return None

    return {
        'entry': entry,
        'stop': stop,
        'tp1': tp1,
        'tp2': tp2,
        'rr1': minimum,
        'rr2': minimum + 1,
        'invalidation': (
            f"확정봉 종가가 "
            f"{'손절선 아래' if up else '손절선 위'}"
            f"에서 마감"
        ),
        'basis': (
            '확정봉 종가 기준 가상 진입, '
            '최근 구조/ATR 손절, R배수 목표'
        )
    }


def scan_one(sym, mode):
    frames = (
        ['15m', '30m', '1H']
        if mode == 'scalp'
        else ['1H', '4H', '1D']
    )

    lower, setup, higher = [
        analyze(sym, f) for f in frames
    ]

    lower.pop('rows', None)
    higher.pop('rows', None)

    flow = flow_analysis(
        sym, frames[1], setup
    )

    setup.pop('rows', None)

    ls = score_direction(
        setup,
        higher['trend'],
        flow,
        'LONG',
        lower
    )
    ss = score_direction(
        setup,
        higher['trend'],
        flow,
        'SHORT',
        lower
    )

    direction = (
        'LONG' if ls >= ss else 'SHORT'
    )
    chosen = max(ls, ss)

    aligned = (
        setup['trend'] == (
            'UP' if direction == 'LONG'
            else 'DOWN'
        )
        and higher['trend'] == setup['trend']
    )

    opposite = (
        'bearish'
        if direction == 'LONG'
        else 'bullish'
    )

    flow_ok = flow['state'] == (
        'BUY' if direction == 'LONG'
        else 'SELL'
    )

    safe = (
        not setup['fake_breakout']
        and setup['divergence'] != opposite
        and lower['divergence'] != opposite
    )

    plan = scenario(
        setup, direction, mode
    )

    valid = (
        chosen >= 65
        and aligned
        and flow_ok
        and safe
        and plan is not None
    )

    reasons = []

    if not aligned:
        reasons.append('상위봉 추세 불일치')

    if not flow_ok:
        reasons.append('수급 추정치 미확인/반대')

    if not safe:
        reasons.append('다이버전스/돌파 경고')

    if plan is None:
        reasons.append('가격 시나리오 불가')

    if chosen < 65:
        reasons.append('점수 부족')

    return {
        'symbol': sym,
        'mode': mode,
        'signal': (
            direction if valid else 'WAIT'
        ),
        'lean': direction,
        'long_score': ls,
        'short_score': ss,
        'setup': setup,
        'higher': higher['trend'],
        'trigger': lower['divergence'],
        'flow': flow,
        'plan': plan if valid else None,
        'status': (
            '조건부 후보 · 실제 진입 전 확인'
            if valid else '관망'
        ),
        'reason': (
            ', '.join(reasons)
            if reasons
            else '조건 충족 (수익 보장 아님)'
        )
    }


MAJORS = [
    'BTCUSDT',
    'ETHUSDT',
    'SOLUSDT',
    'XRPUSDT',
    'BNBUSDT',
    'DOGEUSDT',
    'ADAUSDT',
    'LINKUSDT',
    'AVAXUSDT',
    'SUIUSDT'
]


@app.route('/api/majors')
def majors():
    mode = request.args.get('mode', 'scalp')

    if mode not in ('scalp', 'swing'):
        return jsonify(
            error='잘못된 분석 모드'
        ), 400

    try:
        available = {
            s for s, _ in symbols(0)
        }
    except Exception as e:
        return jsonify(
            error=(
                'Bitget 종목 목록 조회 실패: '
                + str(e)
            )
        ), 502

    results, errors = [], []
    selected = [
        s for s in MAJORS
        if s in available
    ]

    for s in MAJORS:
        if s not in available:
            errors.append({
                'symbol': s,
                'error': (
                    '현재 USDT 선물 종목 목록에 없음'
                )
            })

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(scan_one, s, mode): s
            for s in selected
        }

        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                errors.append({
                    'symbol': futures[fut],
                    'error': str(e)[:120]
                })

    results.sort(
        key=lambda x: MAJORS.index(x['symbol'])
    )

    return jsonify(
        results=results,
        errors=errors,
        server_time=int(time.time())
    )


@app.route('/')
def home():
    return render_template_string(BADANG_ORIGINAL_HTML)


@app.route('/api/scan')
def scan():
    mode = request.args.get(
        'mode', 'scalp'
    )
    mode = (
        mode if mode in ('scalp', 'swing')
        else 'scalp'
    )

    try:
        minimum = max(
            0,
            float(
                request.args.get(
                    'min_turnover', 1000000
                )
            )
        )
    except ValueError:
        return jsonify(
            error='거래대금 설정 오류'
        ), 400

    try:
        syms = symbols(minimum)
    except Exception as e:
        return jsonify(
            error=(
                'Bitget 종목 조회 실패: '
                + str(e)
            )
        ), 502

    try:
        offset = max(
            0,
            int(request.args.get('offset', 0))
        )
    except ValueError:
        offset = 0

    batch = syms[offset:offset+5]
    results, errors = [], []

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(scan_one, s, mode): s
            for s, _ in batch
        }

        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                errors.append({
                    'symbol': futures[fut],
                    'error': str(e)[:120]
                })

    return jsonify(
        total=len(syms),
        offset=offset,
        next_offset=offset+len(batch),
        results=results,
        errors=errors,
        server_time=int(time.time()),
        recommendations=recommend_candidates(results)
    )


def recommend_candidates(
    results, min_score=80, min_rr=1.5
):
    candidates = []

    for item in results:
        direction = item.get('signal')

        if direction not in ('LONG', 'SHORT'):
            continue

        score = item.get(
            'long_score'
            if direction == 'LONG'
            else 'short_score',
            0
        )

        if score < min_score:
            continue

        plan = item.get('plan')

        if not isinstance(plan, dict):
            continue

        entry = plan.get('entry')
        stop = plan.get('stop')
        tp1 = plan.get('tp1')

        if any(
            v is None
            for v in (entry, stop, tp1)
        ):
            continue

        risk = abs(entry - stop)
        reward = abs(tp1 - entry)

        if (
            risk <= 0
            or reward / risk < min_rr
        ):
            continue

        if (
            direction == 'LONG'
            and not (stop < entry < tp1)
        ):
            continue

        if (
            direction == 'SHORT'
            and not (tp1 < entry < stop)
        ):
            continue

        candidate = dict(item)
        candidate['recommend_score'] = score
        candidate['recommend_direction'] = direction
        candidate['risk_reward'] = round(
            reward / risk, 2
        )

        candidates.append(candidate)

    return sorted(
        candidates,
        key=lambda x: x['recommend_score'],
        reverse=True
    )


@app.route('/api/test-exchanges')
def test_exchanges():
    from exchange_data import fastest_candles

    symbol = request.args.get(
        'symbol', 'BTCUSDT'
    )
    timeframe = request.args.get(
        'timeframe', '5m'
    )

    if timeframe not in (
        '5m', '15m', '30m',
        '1H', '4H', '1D'
    ):
        return jsonify(
            error='Invalid timeframe'
        ), 400

    exchange = request.args.get(
        'exchange', 'auto'
    ).lower()

    exchanges = (
        None if exchange == 'auto'
        else (exchange,)
    )

    if exchange not in (
        'auto', 'bitget',
        'binance', 'okx'
    ):
        return jsonify(
            error='Invalid exchange'
        ), 400

    try:
        result = fastest_candles(
            symbol,
            timeframe,
            exchanges=exchanges
        )

        return jsonify(
            status='ok',
            exchange=result['exchange'],
            symbol=result['symbol'],
            timeframe=result['timeframe'],
            candle_count=len(result['candles']),
            latency_ms=result['latency_ms']
        )

    except Exception as e:
        return jsonify(
            status='error',
            error=str(e)
        ), 502


@app.route('/api/v13-test')
def v13_test():
    from exchange_data import fastest_candles
    from badang_analysis_v13 import analyze

    try:
        symbol = request.args.get(
            'symbol', 'BTCUSDT'
        )

        result = fastest_candles(
            symbol,
            '15m',
            exchanges=['bitget', 'okx']
        )

        analysis = analyze(
            result['candles'],
            mode='scalp',
            symbol=symbol
        )

        analysis['exchange'] = result['exchange']

        return jsonify(analysis)

    except Exception as e:
        return jsonify(
            error=str(e)
        ), 502


def stabilize_trade_plan(item):
    """Reject impossible prices; never turn a malformed plan into a signal."""
    if item.get('status') != 'ok':
        return item
    entry = finite_number(item.get('entry_reference'))
    stop = finite_number(item.get('stop_loss'))
    tp1 = finite_number(item.get('take_profit_1'))
    tp2 = finite_number(item.get('take_profit_2'))
    side = item.get('candidate_side')
    valid = (all(v is not None and v > 0 for v in (entry, stop, tp1, tp2))
             and ((side == 'LONG' and stop < entry < tp1 < tp2)
                  or (side == 'SHORT' and tp2 < tp1 < entry < stop)))
    if not valid:
        item['recommendation'] = 'WAIT'
        item['take_profit_1'] = None
        item['take_profit_2'] = None
        item['risk_reward_1'] = None
        item.setdefault('stability_warnings', []).append('INVALID_TRADE_PLAN')
    return item


def check_flow_conflict(item):
    """Strong opposing *sample* flow vetoes a directional suggestion."""
    research = item.get('v17_research') or {}
    imbalance = finite_number(research.get('sample_imbalance'))
    count = research.get('trade_sample_count') or 0
    side = item.get('recommendation')
    if (imbalance is None
            or count < 40 or side not in ('LONG', 'SHORT')):
        return item
    conflict = (side == 'LONG' and imbalance <= -0.12) or (side == 'SHORT' and imbalance >= 0.12)
    if conflict:
        item['recommendation'] = 'WAIT'
        item.setdefault('stability_warnings', []).append('OPPOSING_RECENT_TRADE_SAMPLE')
        research.setdefault('checks', {})['recent_trade_sample_conflicts'] = True
    else:
        research.setdefault('checks', {})['recent_trade_sample_conflicts'] = False
    return item


def structure_levels(candles, entry, side, lookback=40):
    """Descriptive closed-candle range, not an entry signal or prediction.

    Excludes newest candle (possibly still forming). Requires at least 20
    valid earlier OHLC candles. Does not change recommendation or trade plan.
    """
    try:
        entry = finite_number(entry)
        if entry is None or entry <= 0 or side not in ('LONG', 'SHORT'):
            return {'status': 'UNAVAILABLE', 'reason': '기준 가격 또는 방향 확인 불가'}
        rows = list(candles or [])
        prior = rows[:-1][-lookback:]
        valid = []
        for row in prior:
            if len(row) < 5:
                continue
            high, low = finite_number(row[2]), finite_number(row[3])
            if high is not None and low is not None and 0 < low <= high:
                valid.append((high, low))
        if len(valid) < 20:
            return {'status': 'UNAVAILABLE', 'reason': '확인 가능한 이전 캔들 20개 미만'}
        support = min(low for _, low in valid)
        resistance = max(high for high, _ in valid)
        if support >= resistance:
            return {'status': 'UNAVAILABLE', 'reason': '가격 범위 산정 불가'}
        width_pct = (resistance - support) / entry * 100
        if entry > resistance:
            location = 'ABOVE_RANGE'
        elif entry < support:
            location = 'BELOW_RANGE'
        else:
            location = 'INSIDE_RANGE'
        near_pct = 0.3  # Fixed illustrative proximity, not volatility adjusted.
        near_support = abs(entry - support) / entry * 100 <= near_pct
        near_resistance = abs(entry - resistance) / entry * 100 <= near_pct
        return {
            'status': 'AVAILABLE', 'method': 'PREVIOUS_CANDLES_RANGE',
            'lookback_used': len(valid), 'excludes_latest_candle': True,
            'support_reference': support, 'resistance_reference': resistance,
            'position': location, 'range_width_pct': round(width_pct, 3),
            'near_support': near_support, 'near_resistance': near_resistance,
            'proximity_threshold_pct': near_pct,
            'breakout_confirmed': False, 'retest_confirmed': False,
            'note': '최근 이전 캔들의 최고·최저 범위. 실제 지지·저항이나 돌파·재시험을 확정하지 않음'
        }
    except (TypeError, ValueError, IndexError):
        return {'status': 'UNAVAILABLE', 'reason': '캔들 자료 형식 오류'}




def wave_confluence_review(candidate, candle_rows, research=None, candle_exchange=None):
    """Read-only Elliott/Fibonacci/volume confluence; never a trading signal."""
    points = candidate.get('pivot_points') or []
    result = {'status': 'UNAVAILABLE', 'fib': {}, 'volume': {},
              'flow': {'status': 'NOT_LINKED'},
              'warnings': [], 'interpretation': '검증할 전환점이 부족합니다.'}
    if len(points) not in (4, 6):
        return result
    try:
        prices = [float(p['price']) for p in points]
        indices = [int(p['bar_index']) for p in points]
        if any(not math.isfinite(p) or p <= 0 for p in prices):
            return result
        if indices != sorted(indices) or len(set(indices)) != len(indices):
            return result
        if indices[-1] >= len(candle_rows) - 1:
            result['warnings'].append('마지막 미완료 캔들 포함 가능성')
            return result
        result['status'] = 'AVAILABLE'
        result['fib'] = {'status': 'NOT_APPLICABLE'}
        if len(prices) == 6:
            p0, p1, p2, p3, p4, p5 = prices
            length1, length3, length5 = abs(p1-p0), abs(p3-p2), abs(p5-p4)
            # Fundamental impulse constraints: independent of Fibonacci preferences.
            # These are candidate checks, not evidence that the wave has completed.
            down = p1 < p0
            directional = (p3 < p1 and p5 < p3) if down else (p3 > p1 and p5 > p3)
            wave2_invalid = (p2 >= p0) if down else (p2 <= p0)
            # Standard non-diagonal impulse: wave 4 must not overlap wave 1 territory.
            wave4_overlap = (p4 >= p1) if down else (p4 <= p1)
            wave3_shortest = length3 < min(length1, length5)
            failures = []
            if not directional: failures.append('1·3·5파의 진행 방향 또는 새 고점·저점 조건 불일치')
            if wave2_invalid: failures.append('2파가 파동 시작점을 침범함')
            if wave4_overlap: failures.append('4파가 1파 가격 영역과 겹침 (일반 추진파 기준)')
            if wave3_shortest: failures.append('3파가 1·3·5파 중 가장 짧음')
            result['impulse_rules_38'] = {
                'status': 'CONFLICT' if failures else 'BASIC_RULES_PASS',
                'failures': failures,
                'note': '일반 추진파 기준이며 대각삼각형 등 예외 패턴을 자동 확정하지 않음'
            }
            if min(length1, length3) > 0:
                result['fib'] = {
                    'status': 'AVAILABLE',
                    'wave2_retracement': round(abs(p2-p1)/length1, 4),
                    'wave3_to_wave1': round(length3/length1, 4),
                    'wave4_retracement': round(abs(p4-p3)/length3, 4),
                    'wave5_to_wave1': round(length5/length1, 4),
                    'wave5_vs_wave1_0618': round(p4 + (1 if p5 > p4 else -1)*length1*.618, 8),
                    'wave5_vs_wave1_1000': round(p4 + (1 if p5 > p4 else -1)*length1, 8),
                }
        def segment_volume(a, b):
            vals = []
            for row in candle_rows[a+1:b+1]:
                if len(row) < 6:
                    continue
                v = finite_number(row[5])
                if v is not None and v >= 0:
                    vals.append(v)
            return sum(vals)/len(vals) if vals else None
        if len(prices) == 6:
            v3 = segment_volume(indices[2], indices[3])
            v5 = segment_volume(indices[4], indices[5])
            result['volume'] = {
                'wave3_avg_candle_volume': v3,
                'wave5_avg_candle_volume': v5,
                'wave5_vs_wave3_ratio': round(v5/v3, 3) if v3 and v5 is not None else None,
                'note': '파동 구간별 캔들 평균 거래량 비교. 체결 방향이나 순매수 금액 아님'
            }
        research = research or {}
        source = research.get('source_exchange')
        if source and candle_exchange and source != candle_exchange:
            result['warnings'].append('파생상품 지표와 파동 캔들의 거래소가 달라 직접적인 파동별 수급 비교 불가')
        result['flow'] = {'status': 'NOT_WAVE_ALIGNED',
                          'note': 'OI·펀딩·표본 CVD는 파동 시작~끝과 같은 시간 구간의 완전한 자료가 아니므로 파동별 확증에 사용하지 않음'}
        result['interpretation'] = '파동 구조에 피보나치 비율과 구간 거래량을 대조한 참고 결과. 파동 종료 또는 반전 확정 아님.'
        return result
    except (ValueError, TypeError, IndexError, KeyError, ZeroDivisionError):
        return result



def verify_wave_evidence_44(candidate, timeframe, trend, source_exchange):
    """Conservative, explainable wave evidence. Never changes trading scores."""
    conf = candidate.get('confluence_36') or {}
    rules = conf.get('impulse_rules_38') or {}
    fib = conf.get('fib') or {}
    volume = conf.get('volume') or {}
    pattern = candidate.get('pattern')
    direction = candidate.get('direction')
    conflicts, supports, unknown = [], [], []
    if candidate.get('structure_status') != 'TIME_ORDER_VALID':
        conflicts.append('전환점 시간 순서 검증 실패')
    if pattern == '5-wave impulse candidate':
        if rules.get('status') == 'CONFLICT' or candidate.get('impulse_rule_status') == 'INVALID':
            conflicts.append('기본 추진파 규칙과 충돌')
        elif rules.get('status') == 'BASIC_RULES_PASS':
            supports.append('기본 추진파 규칙에서 명백한 위반 없음')
        else:
            unknown.append('파동 기본 규칙 검증 부족')
        if fib.get('status') == 'AVAILABLE':
            r2 = finite_number(fib.get('wave2_retracement'))
            r4 = finite_number(fib.get('wave4_retracement'))
            if r2 is not None and r4 is not None:
                if r2 >= 1 or r4 >= 1:
                    conflicts.append('되돌림이 이전 파동 전체를 침범')
                elif r2 > .85 or r4 > .85:
                    unknown.append('되돌림이 깊어 파동 시작점 재확인 필요')
                else:
                    supports.append('되돌림 비율에 큰 구조 충돌 없음')
            else:
                unknown.append('피보나치 계산 자료 부족')
        else:
            unknown.append('피보나치 검증 자료 부족')
        vr = finite_number(volume.get('wave5_vs_wave3_ratio'))
        if vr is None:
            unknown.append('파동 구간 거래량 비교 불가')
        elif vr < .85:
            supports.append('5파 구간 거래량 감소 관찰(종료 확정 아님)')
        else:
            unknown.append('거래량만으로 파동 종료 확인 불가')
    else:
        unknown.append('ABC 조정은 현재 비율·거래량 독립 검증 부족')
    relation = candidate.get('temporal_relation_39') or {}
    if relation.get('status') in ('TIME_CONTAINED_UNVERIFIED','PARTIAL_OVERLAP_UNVERIFIED'):
        unknown.append('상위 시간봉과 중복 가능성: 독립 확인 아님')
    elif relation.get('status') == 'NO_COMPARABLE_PARENT':
        unknown.append('상위 시간봉 파동 비교 불가')
    expected = 'UP' if direction in ('UP','LONG','bullish','up') else ('DOWN' if direction in ('DOWN','SHORT','bearish','down') else None)
    if expected and trend in ('UP','DOWN'):
        if expected == trend: supports.append('해당 시간봉의 이동평균 추세와 방향 일치')
        else: unknown.append('해당 시간봉의 추세와 반대: 역추세 후보')
    else:
        unknown.append('추세와 파동 방향 비교 불가')
    if conf.get('flow',{}).get('status') != 'WAVE_ALIGNED_CONFIRMED':
        unknown.append('OI·펀딩·CVD는 동일 파동 구간 수급으로 검증되지 않음')
    if conf.get('warnings'):
        unknown.extend(conf['warnings'])
    status = 'STRUCTURE_CONFLICT' if conflicts else 'PARTIAL_EVIDENCE' if supports else 'INSUFFICIENT_EVIDENCE'
    return {'status':status, 'supports':supports, 'conflicts':conflicts,
            'unverified':unknown, 'independent_confirmation':False,
            'reversal_confirmed':False, 'completion_confirmed':False,
            'source_exchange':source_exchange, 'timeframe':timeframe,
            'note':'파동 근거 점검 결과이며 승률·진입 신호·반등 확정이 아님'}


def breakout_retest_review(candles, lookback=20):
    """Conservative descriptive study of *closed* OHLCV bars only.

    The newest bar is omitted because the exchange adapter does not certify
    whether it has closed. This is not an execution signal.
    """
    unavailable = lambda reason: {'status': 'UNAVAILABLE', 'stage': 'DATA_UNAVAILABLE', 'reason': reason}
    try:
        bars = []
        for row in list(candles or [])[:-1]:
            if len(row) < 6:
                return unavailable('거래량 포함 OHLCV 자료가 부족함')
            op,hi,lo,cl,vol = [finite_number(row[i]) for i in (1,2,3,4,5)]
            if any(v is None for v in (op,hi,lo,cl,vol)) or min(op,lo,cl) <= 0 or hi < max(op,cl,lo) or vol < 0:
                return unavailable('유효하지 않은 캔들 자료')
            bars.append((op,hi,lo,cl,vol, row[0] if row else None))
        if len(bars) < lookback+6:
            return unavailable('완료된 캔들 수 부족')
        # Evaluate most recent 6 closed candles for a breakout against the 20
        # immediately preceding bars. A retest requires at least one later bar.
        for i in range(len(bars)-1, len(bars)-7, -1):
            if i < lookback: break
            prior = bars[i-lookback:i]
            top=max(v[1] for v in prior); bottom=min(v[2] for v in prior)
            op,hi,lo,cl,vol,_timestamp=bars[i]
            direction = 'UP' if cl>top and bars[i-1][3]<=top else 'DOWN' if cl<bottom and bars[i-1][3]>=bottom else None
            if direction is None: continue
            level=top if direction=='UP' else bottom
            baseline=sum(v[4] for v in prior)/lookback
            ratio=vol/baseline if baseline>0 else None
            later=bars[i+1:]
            tolerance=0.0025 # 0.25% illustrative band, not volatility-adjusted
            retest=False
            retest_index=None
            retest_price=None
            retest_time=None
            for j,b in enumerate(later):
                if direction=='UP' and b[2]<=level*(1+tolerance) and b[3]>level:
                    retest=True
                    retest_index=j
                    retest_price=b[3]
                    retest_time=b[5]
                if direction=='DOWN' and b[1]>=level*(1-tolerance) and b[3]<level:
                    retest=True
                    retest_index=j
                    retest_price=b[3]
                    retest_time=b[5]
            invalidated=any((b[3]<level*(1-tolerance) if direction=='UP' else b[3]>level*(1+tolerance)) for b in later)
            stage='INVALIDATED' if invalidated else 'RETEST_CANDIDATE' if retest else 'AWAIT_RETEST' if later else 'BREAKOUT_OBSERVED'
            return {'status':'AVAILABLE','stage':stage,'direction':direction,'level':round(level,10),
                    'bars_since_breakout':len(later),'retest_price':round(retest_price,10) if retest_price is not None else None,'retest_time':retest_time,'bars_since_retest':len(later)-1-retest_index if retest_index is not None else None,'breakout_time':bars[i][5],'latest_closed_price':round(bars[-1][3],10),'currently_beyond_level':(bars[-1][3]>level if direction=='UP' else bars[-1][3]<level),'reference_lookback':lookback,'breakout_volume_ratio':round(ratio,3) if ratio is not None else None,
                    'volume_increased':ratio is not None and ratio>=1.2,
                    'closed_candles_only':True,'retest_tolerance_pct':0.25,
                    'note':'종가와 가격 범위에 근거한 후보 분류. 돌파·재시험의 신뢰도나 진입 적합성은 검증되지 않음'}
        return {'status':'AVAILABLE','stage':'NO_BREAKOUT','closed_candles_only':True,
                'reference_lookback':lookback,'note':'최근 완료된 캔들 6개에서 이전 20개 캔들 범위의 신규 종가 돌파를 발견하지 못함'}
    except (ValueError,TypeError,IndexError):
        return unavailable('캔들 분석 오류')

def price_action_45(candles, trends, mode):
    """Closed-candle, non-lookahead breakout/retest/reversal candidates.

    Prices are indicative candle closes, not live execution quotes.
    """
    try:
        rows = [[float(v) for v in row[1:6]] for row in candles[:-1]]
        if len(rows) < 45 or any(not all(math.isfinite(v) and v > 0 for v in r[:4]) for r in rows[-35:]):
            return {'side': 'WAIT', 'reason': '확정 캔들 자료 부족'}
        # source OHLCV = timestamp, open, high, low, close, volume
        cur, prev = rows[-1], rows[-2]
        op, hi, lo, cl, vol = cur
        history = rows[-17:-1]
        resistance = max(r[1] for r in history)
        support = min(r[2] for r in history)
        recent = rows[-5:-1]
        avg_vol = sum(r[4] for r in rows[-21:-1]) / 20
        vol_ok = avg_vol > 0 and vol >= avg_vol * 1.10
        # Breakout or break-down on a closed candle, not intrabar wick.
        bull_break = cl > resistance and cl > op and vol_ok
        bear_break = cl < support and cl < op and vol_ok
        # Retest: prior close beyond a level; latest candle tests and closes back beyond it.
        prior_res = max(r[1] for r in rows[-18:-2])
        prior_sup = min(r[2] for r in rows[-18:-2])
        bull_retest = prev[3] > prior_res and lo <= prior_res * 1.003 and cl > prior_res and cl > op
        bear_retest = prev[3] < prior_sup and hi >= prior_sup * .997 and cl < prior_sup and cl < op
        # Reversal requires an actual reclaim/rejection and directional candle.
        low_lookback = min(r[2] for r in rows[-13:-1])
        high_lookback = max(r[1] for r in rows[-13:-1])
        bull_turn = (lo <= low_lookback * 1.003 and cl > prev[1] and cl > op
                     and cl > (hi+lo)/2 and vol_ok)
        bear_turn = (hi >= high_lookback * .997 and cl < prev[2] and cl < op
                     and cl < (hi+lo)/2 and vol_ok)
        options = []
        for side, kind, condition, level in (
            ('LONG', '돌파', bull_break, resistance),
            ('SHORT', '하향 이탈', bear_break, support),
            ('LONG', '돌파 후 지지 확인', bull_retest, prior_res),
            ('SHORT', '이탈 후 저항 확인', bear_retest, prior_sup),
            ('LONG', '저점 반등', bull_turn, low_lookback),
            ('SHORT', '고점 반락', bear_turn, high_lookback),
        ):
            if condition:
                options.append((side, kind, level))
        if not options:
            return {'side':'WAIT', 'reason':'최근 확정봉에서 돌파·재시험·반전 조건 미확인',
                    'support':support,'resistance':resistance}
        # Prefer breakout/retest over reversals, and trend-following when tied.
        options.sort(key=lambda z: (z[1] in ('저점 반등','고점 반락'),
                                    trends.get('30m' if mode=='scalp' else '4H') != ('UP' if z[0]=='LONG' else 'DOWN')))
        side, kind, level = options[0]
        direction = 1 if side == 'LONG' else -1
        true_ranges = [max(r[1]-r[2],abs(r[1]-rows[i-1][3]),abs(r[2]-rows[i-1][3]))
                       for i,r in enumerate(rows[-16:],start=len(rows)-16) if i>0]
        atr = sum(true_ranges[-14:])/max(1,len(true_ranges[-14:]))
        if not math.isfinite(atr) or atr<=0:
            return {'side':'WAIT','reason':'변동성 계산 불가'}
        # Stop beyond nearby structure, with a small volatility buffer.
        structure = min(r[2] for r in rows[-7:]) if direction==1 else max(r[1] for r in rows[-7:])
        stop = min(structure - .15*atr, cl - .8*atr) if direction==1 else max(structure+.15*atr,cl+.8*atr)
        risk = abs(cl-stop)
        if risk/cl > .035 or risk/cl < .0004:
            return {'side':'WAIT','reason':'손절 폭이 과도하거나 비정상적임'}
        # A candle closing too far beyond trigger is chase risk.
        if abs(cl-level) > 1.8*atr:
            return {'side':'WAIT','reason':'신호 발생 뒤 가격이 이미 많이 이동함'}
        target1=cl+direction*1.3*risk
        target2=cl+direction*1.8*risk
        if min(stop,target1,target2)<=0:
            return {'side':'WAIT','reason':'목표가 계산 불가'}
        higher = trends.get('1H' if mode=='scalp' else '1D')
        counter = higher not in (None,'NEUTRAL', 'UP' if side=='LONG' else 'DOWN')
        return {'side':side,'kind':kind,'countertrend':counter,
                'entry':cl,'stop':stop,'tp1':target1,'tp2':target2,
                'rr1':1.3,'rr2':1.8,'trigger_level':level,
                'support':support,'resistance':resistance,
                'volume_ratio':round(vol/avg_vol,2) if avg_vol else None,
                'reason':('역추세 단기 ' if counter else '추세 방향 ')+kind+' 후보 · 확정봉 기준'}
    except (ValueError, TypeError, IndexError, ZeroDivisionError, KeyError) as exc:
        return {'side':'WAIT','reason':'가격 행동 검증 실패: '+type(exc).__name__}


@app.route('/api/v13-scan')
def v13_scan():
    from exchange_data import fastest_candles
    from badang_analysis_v13 import (
        analyze,
        top_five,
        ema,
        normalize,
        pivots,
        wave_candidates
    )

    mode = request.args.get(
        'mode', 'scalp'
    )

    if mode not in ('scalp', 'swing'):
        return jsonify(
            error='Invalid mode'
        ), 400

    try:
        offset = max(
            0,
            int(request.args.get('offset', 0))
        )

        requested_symbol = request.args.get('symbol', '').strip().upper()
        if requested_symbol:
            # Individual USDT perpetual search; candle providers verify listing.
            if not re.fullmatch(r'[A-Z0-9]{2,25}USDT', requested_symbol):
                return jsonify(error='USDT 선물 종목을 입력하세요. 예: XRPUSDT'), 400
            universe = [requested_symbol]
        else:
            universe = ['BTCUSDT', 'ETHUSDT'] + [
                s for s, _ in symbols(1000000)
                if s not in ('BTCUSDT', 'ETHUSDT')
            ]

        batch = universe[offset:offset+1]
        results, errors = [], []
        candle_map = {}

        frames = (
            ['15m', '30m', '1H']
            if mode == 'scalp'
            else ['1H', '4H', '1D']
        )

        for symbol in batch:
            try:
                frame_data = {}

                for tf in frames:
                    frame_data[tf] = fastest_candles(
                        symbol,
                        tf,
                        exchanges=['bitget', 'okx']
                    )

                data = frame_data[frames[0]]

                item = analyze(
                    data['candles'],
                    mode=mode,
                    symbol=symbol
                )

                trends = {}

                for tf in frames:
                    rows = frame_data[tf]['candles']
                    closes = [
                        float(row[4])
                        for row in rows
                    ]

                    e20 = ema(closes, 20)[-1]
                    e50 = ema(closes, 50)[-1]

                    trends[tf] = (
                        'UP' if e20 > e50
                        else 'DOWN' if e20 < e50
                        else 'NEUTRAL'
                    )

                # 3.2: Compare confirmed higher-timeframe structures first.
                # Separate read-only wave interpretation from trade scoring.
                wave_by_tf = {}
                hierarchy = (['1H', '30m', '15m'] if mode == 'scalp'
                             else ['1D', '4H', '1H'])
                for tf in hierarchy:
                    try:
                        candles = frame_data[tf]['candles']
                        # All timestamps are in the exchange's original candle data.
                        closed = candles[:-1]
                        rows = normalize(closed)
                        if len(rows) < 35:
                            wave_by_tf[tf] = {'status': 'INSUFFICIENT_DATA',
                                               'candidates': []}
                            continue
                        # Try both tighter and broader pivots. Avoid treating a
                        # short sequence of tiny swings as the entire wave.
                        views = []
                        for radius in (3, 6):
                            turns = pivots(rows, radius=radius)
                            candidates = wave_candidates(turns)
                            candidates = [dict(c) for c in candidates]
                            for c in candidates:
                                c['pivot_points'] = [
                                    dict(pt, candle_time=closed[pt['bar_index']][0])
                                    for pt in c.get('pivot_points', [])
                                    if isinstance(pt.get('bar_index'), int)
                                    and 0 <= pt['bar_index'] < len(closed)
                                ]
                                c['radius'] = radius
                                c['start_bar'] = c['pivot_points'][0]['bar_index'] if c['pivot_points'] else None
                                c['end_bar'] = c['pivot_points'][-1]['bar_index'] if c['pivot_points'] else None
                                c['bars_since_last_pivot'] = (
                                    len(closed) - 1 - c['end_bar']
                                    if c['end_bar'] is not None else None
                                )
                            views.append({'radius': radius, 'candidates': candidates})
                        max_age = {'15m': 12, '30m': 9, '1H': 7, '4H': 6, '1D': 5}.get(tf, 7)
                        for view in views:
                            for c in view['candidates']:
                                age = c.get('bars_since_last_pivot')
                                c['age_class'] = 'RECENT' if age is not None and age <= max_age else 'HISTORICAL'
                                c['completion'] = 'UNCONFIRMED'
                        broad = [c for c in views[1]['candidates'] if c['age_class'] == 'RECENT']
                        narrow = [c for c in views[0]['candidates'] if c['age_class'] == 'RECENT']
                        historical = [c for v in views for c in v['candidates'] if c['age_class'] == 'HISTORICAL']
                        wave_by_tf[tf] = {'status': 'AVAILABLE', 'views': views,
                            'candidates': broad or narrow, 'historical_candidates': historical,
                            'max_age_bars': max_age, 'closed_candles': len(closed)}
                    except (ValueError, TypeError, IndexError, KeyError) as exc:
                        logger.warning('Wave structure unavailable for %s %s: %s',
                                       symbol, tf, exc)
                        wave_by_tf[tf] = {'status': 'UNAVAILABLE',
                                          'candidates': []}
                # 3.4: explicit time/price relationship; no forced nesting.
                for tf, record in wave_by_tf.items():
                    for candidate in record.get('candidates', []):
                        pts = candidate.get('pivot_points', [])
                        try:
                            times = [int(p['candle_time']) for p in pts]
                            prices = [float(p['price']) for p in pts]
                            if (len(times) < 4 or times != sorted(times)
                                    or len(set(times)) != len(times)
                                    or any(p <= 0 for p in prices)):
                                candidate['structure_status'] = 'INVALID_PIVOTS'
                            else:
                                candidate['structure_status'] = 'TIME_ORDER_VALID'
                                candidate['start_time'] = times[0]
                                candidate['end_time'] = times[-1]
                                candidate['start_price'] = prices[0]
                                candidate['end_price'] = prices[-1]
                        except (ValueError, TypeError, KeyError):
                            candidate['structure_status'] = 'INVALID_PIVOTS'
                    record['candidates'] = [c for c in record.get('candidates', [])
                                            if c.get('structure_status') == 'TIME_ORDER_VALID']
                # Relationship is only a descriptive overlap check, NOT
                # Elliott degree confirmation. Compare with first available
                # larger-timeframe candidate and refuse to imply nesting.
                for upper, lower in zip(hierarchy, hierarchy[1:]):
                    up = wave_by_tf.get(upper, {}).get('candidates', [])
                    lo = wave_by_tf.get(lower, {}).get('candidates', [])
                    for c in lo:
                        c['higher_timeframe'] = upper
                        c['higher_relation'] = 'NO_CURRENT_PARENT'
                        if not up:
                            continue
                        parent = up[0]
                        c['higher_relation'] = ('TIME_WINDOW_CONTAINED'
                            if (parent['start_time'] <= c['start_time']
                                and c['end_time'] <= parent['end_time'])
                            else 'DIFFERENT_TIME_WINDOW')
                        c['higher_direction_agrees'] = (
                            parent.get('direction') == c.get('direction'))
                # 3.5: Compare candidates by their actual timestamps and price
                # ranges, not by labels or the timeframe alone.
                def candidate_similarity(a, b):
                    a0, a1 = a['start_time'], a['end_time']
                    b0, b1 = b['start_time'], b['end_time']
                    overlap = max(0, min(a1, b1) - max(a0, b0))
                    union = max(a1, b1) - min(a0, b0)
                    time_ratio = overlap / union if union > 0 else 0.0
                    ap = [float(p['price']) for p in a['pivot_points']]
                    bp = [float(p['price']) for p in b['pivot_points']]
                    ar = (min(ap), max(ap))
                    br = (min(bp), max(bp))
                    price_overlap = max(0.0, min(ar[1], br[1]) - max(ar[0], br[0]))
                    price_union = max(ar[1], br[1]) - min(ar[0], br[0])
                    price_ratio = price_overlap / price_union if price_union > 0 else 0.0
                    # Close endpoints help distinguish two overlapping but
                    # different swings. Relative to their full price range.
                    endpoint_tol = max(price_union * 0.12, 1e-8)
                    close_end = abs(ap[-1] - bp[-1]) <= endpoint_tol
                    same_direction = a.get('direction') == b.get('direction')
                    return {
                        'time_overlap': round(time_ratio, 3),
                        'price_overlap': round(price_ratio, 3),
                        'same_direction': same_direction,
                        'close_endpoints': close_end,
                        'likely_same_move': bool(
                            same_direction and close_end and
                            time_ratio >= 0.35 and price_ratio >= 0.65
                        ),
                    }

                # Explicitly classify 15m/30m overlaps. A common move is not
                # independent confirmation of a higher-degree Elliott count.
                for upper, lower in zip(hierarchy, hierarchy[1:]):
                    upper_candidates = wave_by_tf.get(upper, {}).get('candidates', [])
                    lower_candidates = wave_by_tf.get(lower, {}).get('candidates', [])
                    for candidate in lower_candidates:
                        candidate['cross_tf_comparison'] = 'NO_COMPARABLE_CANDIDATE'
                        candidate['cross_tf_metrics'] = None
                        if not upper_candidates:
                            continue
                        comparisons = [
                            (candidate_similarity(candidate, parent), parent)
                            for parent in upper_candidates
                        ]
                        metrics, parent = max(
                            comparisons,
                            key=lambda pair: (
                                pair[0]['time_overlap'] + pair[0]['price_overlap']
                            )
                        )
                        candidate['cross_tf_metrics'] = metrics
                        if metrics['likely_same_move']:
                            candidate['cross_tf_comparison'] = 'LIKELY_SAME_MOVE'
                        elif metrics['time_overlap'] > 0:
                            candidate['cross_tf_comparison'] = 'OVERLAPPING_UNCONFIRMED'
                        else:
                            candidate['cross_tf_comparison'] = 'SEPARATE_TIME_WINDOWS'
                        candidate['cross_tf_parent_timeframe'] = upper

                # Validate classical non-diagonal impulse constraints again
                # using the exact points displayed to the user.
                for tf, record in wave_by_tf.items():
                    for candidate in record.get('candidates', []):
                        if candidate.get('pattern') != '5-wave impulse candidate':
                            candidate['impulse_rule_status'] = 'NOT_APPLICABLE'
                            continue
                        prices = [float(p['price']) for p in candidate['pivot_points']]
                        if len(prices) != 6:
                            candidate['impulse_rule_status'] = 'INVALID'
                            continue
                        direction = 1 if prices[1] > prices[0] else -1
                        lengths = [abs(prices[i+1] - prices[i]) for i in range(5)]
                        valid = (
                            all((prices[i+1]-prices[i])*direction > 0
                                for i in (0, 2, 4))
                            and all((prices[i+1]-prices[i])*direction < 0
                                    for i in (1, 3))
                            and (prices[2]-prices[0])*direction > 0
                            and lengths[2] >= min(lengths[0], lengths[4])
                            and (prices[4]-prices[1])*direction > 0
                        )
                        candidate['impulse_rule_status'] = (
                            'BASIC_RULES_PASS' if valid else 'INVALID'
                        )
                    record['candidates'] = [
                        c for c in record.get('candidates', [])
                        if c.get('impulse_rule_status') != 'INVALID'
                    ]
                item['wave_by_timeframe_32'] = wave_by_tf
                item['timeframe_trends'] = trends

                # 3.9: Compare actual candidate time windows, without claiming
                # that an Elliott degree relationship or reversal is confirmed.
                def interval_39(c):
                    try:
                        a, b = int(c['start_time']), int(c['end_time'])
                        return (a, b) if a > 0 and b > a else None
                    except (KeyError, TypeError, ValueError):
                        return None

                for upper_tf, lower_tf in zip(hierarchy, hierarchy[1:]):
                    parents = wave_by_tf.get(upper_tf, {}).get('candidates', [])
                    children = wave_by_tf.get(lower_tf, {}).get('candidates', [])
                    for child in children:
                        relation = {'status': 'NO_COMPARABLE_PARENT',
                                    'higher_timeframe': upper_tf,
                                    'note': '상위 시간봉에 비교 가능한 최근 파동 후보 없음'}
                        ci = interval_39(child)
                        valid = [(p, interval_39(p)) for p in parents]
                        valid = [(p, pi) for p, pi in valid if pi]
                        if ci and valid:
                            # Compare closest/most overlapping recent candidate.
                            parent, pi = max(valid, key=lambda z: (
                                max(0, min(ci[1], z[1][1]) - max(ci[0], z[1][0])),
                                -abs(ci[0] - z[1][1])))
                            same = parent.get('direction') == child.get('direction')
                            if pi[0] <= ci[0] and ci[1] <= pi[1]:
                                status = 'TIME_CONTAINED_UNVERIFIED'
                                note = '하위 후보가 상위 후보의 시간 범위 안에 있음. 실제 파동 포함관계는 미확인'
                            elif ci[0] >= pi[1]:
                                status = ('AFTER_PARENT_SAME_DIRECTION' if same
                                          else 'AFTER_PARENT_OPPOSITE_DIRECTION')
                                note = ('상위 후보 종료 뒤 같은 방향 움직임. 추세 연장 여부는 미확인'
                                        if same else
                                        '상위 후보 종료 뒤 반대 방향 움직임. 반등·조정 가능성은 있지만 반전 확정 아님')
                            elif ci[1] <= pi[0]:
                                status = 'BEFORE_PARENT'
                                note = '하위 후보가 상위 후보보다 앞선 시기의 움직임'
                            else:
                                status = 'PARTIAL_OVERLAP_UNVERIFIED'
                                note = '두 후보의 시간이 일부 겹침. 동일 파동인지 별개 파동인지 미확인'
                            relation = {'status': status, 'higher_timeframe': upper_tf,
                                        'higher_direction': parent.get('direction'),
                                        'same_direction': same,
                                        'parent_end_time': pi[1],
                                        'child_start_time': ci[0], 'note': note}
                        child['temporal_relation_39'] = relation

                side = item.get('candidate_side')

                aligned = all(
                    t == (
                        'UP'
                        if side == 'LONG'
                        else 'DOWN'
                    )
                    for t in trends.values()
                )

                item['trend_aligned'] = aligned

                if (
                    item.get('recommendation')
                    in ('LONG', 'SHORT')
                    and not aligned
                ):
                    item['recommendation'] = 'WAIT'

                stabilize_trade_plan(item)
                item['structure_levels'] = structure_levels(
                    data['candles'], item.get('entry_reference'), item.get('candidate_side')
                )
                item['breakout_retest_27'] = breakout_retest_review(data['candles'])
                item['exchange'] = data['exchange']
                item['analysis_timestamp_utc'] = datetime.now(timezone.utc).isoformat()
                item['price_source_exchange'] = data['exchange']
                item['price_timestamp_note'] = '분석 시각(서버 UTC). 거래소 최종 체결 시각이 아님'
                # v1.7.1: avoid duplicate OKX network calls from legacy v1.5.
                # Keep the v1.5 module as a local utility dependency of v1.7.

                # BADANG 1.7: stateless, on-demand research only. No database calls.
                try:
                    item['v17_research'] = research_v18(item, data['candles'])
                except Exception as v17_exc:
                    logger.warning('v1.7 research unavailable for %s: %s', symbol, v17_exc)
                    item['v17_research'] = {
                        'status': 'UNAVAILABLE', 'eligible_for_alert': False,
                        'reason': '1.7 보조 분석 조회 실패'
                    }

                # Populate the primary analysis fields with *sourced* OKX values.
                # They are cross-exchange context if candle source is Bitget.
                research = item.get('v17_research') or {}
                item['funding_rate'] = research.get('funding_rate')
                item['oi_change_pct'] = research.get('oi_change_1h_pct')
                item['futures_data_available'] = {
                    'funding': research.get('funding_rate') is not None,
                    'oi': research.get('oi_contracts') is not None,
                    'oi_history': research.get('oi_change_1h_pct') is not None
                }
                item['derivatives_source_exchange'] = research.get('source_exchange')
                item['derivatives_same_exchange'] = item.get('exchange') == research.get('source_exchange')
                item['cvd_quality'] = 'CONTINUOUS_POLL_UNVERIFIED' if research.get('collection') == 'CONTINUOUS_REST_POLL_BTC_ETH' else 'SAMPLE_ONLY'
                item['vwap_quality'] = 'CANDLE_APPROX_AND_TRADE_SAMPLE'
                # Personal decision-support mode: partial flow is context, not a blanket veto.
                # Scores are indicator agreement, NOT estimated win probability.
                item['technical_score'] = max(item.get('long_score') or 0, item.get('short_score') or 0)
                item['technical_side'] = item.get('candidate_side')
                trend_values = list((item.get('timeframe_trends') or {}).values())
                if trend_values and all(v == 'DOWN' for v in trend_values) and item['technical_side'] == 'LONG':
                    item['trend_score_context_38'] = 'COUNTER_TREND_REBOUND'
                elif trend_values and all(v == 'UP' for v in trend_values) and item['technical_side'] == 'SHORT':
                    item['trend_score_context_38'] = 'COUNTER_TREND_PULLBACK'
                elif trend_values and all(v == ('UP' if item['technical_side'] == 'LONG' else 'DOWN') for v in trend_values):
                    item['trend_score_context_38'] = 'WITH_TREND'
                else:
                    item['trend_score_context_38'] = 'MIXED_OR_UNKNOWN'
                item['data_quality'] = {
                    'candles': 'AVAILABLE',
                    'trade_coverage': 'CONFIRMED' if (research.get('trade_window') or {}).get('coverage_confirmed') else 'UNVERIFIED',
                    'derivatives_exchange': research.get('source_exchange'),
                    'candle_exchange': item.get('exchange'),
                    'cross_exchange': item.get('exchange') != research.get('source_exchange'),
                }
                caveats = []
                if item['data_quality']['trade_coverage'] != 'CONFIRMED':
                    caveats.append('체결 CVD는 일부 수집 표본이며 전체 시장 체결이 아님')
                if item['data_quality']['cross_exchange']:
                    caveats.append('캔들과 파생상품 지표의 거래소가 다름')
                if research.get('status') == 'UNAVAILABLE':
                    caveats.append('파생상품 보조 분석을 조회하지 못함')
                item['data_caveats'] = caveats
                # 3.6: evaluate confluence on the exact same candle source and
                # timeframe as each displayed wave, without altering scores.
                for wave_tf, wave_record in wave_by_tf.items():
                    source_rows = frame_data[wave_tf]['candles']
                    source_exchange = frame_data[wave_tf]['exchange']
                    for view in wave_record.get('views', []):
                        for candidate in view.get('candidates', []):
                            candidate['confluence_36'] = wave_confluence_review(
                                candidate, source_rows, research, source_exchange
                            )
                    for candidate in wave_record.get('candidates', []):
                        if 'confluence_36' not in candidate:
                            candidate['confluence_36'] = wave_confluence_review(
                                candidate, source_rows, research, source_exchange
                            )
                    # 4.4: explicit evidence verdict for every displayed candidate.
                    for view in wave_record.get('views', []):
                        for candidate in view.get('candidates', []):
                            candidate['evidence_44'] = verify_wave_evidence_44(
                                candidate, wave_tf, trends.get(wave_tf), source_exchange)
                    for candidate in wave_record.get('candidates', []):
                        if 'evidence_44' not in candidate:
                            candidate['evidence_44'] = verify_wave_evidence_44(
                                candidate, wave_tf, trends.get(wave_tf), source_exchange)

                # 4.5: actual closed-candle trigger takes precedence over indicator scores.
                action = price_action_45(data['candles'], trends, mode)
                item['price_action_45'] = action
                side = action.get('side','WAIT')
                score = item.get('long_score', 0) if side == 'LONG' else item.get('short_score', 0)
                valid = (item.get('status') == 'ok' and side in ('LONG','SHORT')
                         and action.get('entry') and action.get('stop'))
                item['recommendation'] = side if valid else 'WAIT'
                item['signal_grade'] = ('EARLY_COUNTERTREND' if action.get('countertrend') else 'PRICE_ACTION_CANDIDATE') if valid else 'WAIT'
                item['entry_blockers'] = [] if valid else [action.get('reason','PRICE_ACTION_NOT_CONFIRMED')]
                if valid:
                    item['candidate_side'] = side
                    item['entry_reference'] = action['entry']
                    item['stop_loss'] = action['stop']
                    item['take_profit_1'] = action['tp1']
                    item['take_profit_2'] = action['tp2']
                    item['risk_reward_1'] = action['rr1']
                    item['risk_reward_2'] = action['rr2']
                item['signal_type'] = 'CLOSED_CANDLE_PRICE_ACTION_CANDIDATE_NOT_ORDER'
                item['score_is_win_probability'] = False

                # Keep the exact confirmed candle reference
                # for 1.4 signal history.
                candle_map[symbol] = data['candles']

                results.append(item)

            except Exception as exc:
                errors.append({
                    'symbol': symbol,
                    'error': str(exc)
                })

        # BADANG 1.7: persistence intentionally disabled (free stateless mode).
        storage = {'saved': 0, 'duplicates': 0, 'skipped': 0,
                   'storage': 'disabled_stateless_v171'}

        return jsonify(
            total=len(universe),
            offset=offset,
            next_offset=offset+len(batch),
            results=results,
            recommendations=top_five(results),
            errors=errors,
            signal_storage=storage
        )

    except Exception as exc:
        return jsonify(
            error=str(exc)
        ), 502


# ============================================================
# BADANG 1.4: Signal history API
# ============================================================

@app.route('/api/v14-signals')
def v14_signals():
    return jsonify(status='DISABLED', reason='BADANG 1.7 stateless mode; signal history is not stored', signals=[])


@app.route('/api/v14-db-status')
def v14_db_status():
    return jsonify(status='DISABLED', database='none', connected=False,
                   reason='BADANG 1.7 does not use PostgreSQL')


BADANG_ORIGINAL_HTML = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0c1424"><title>BADANG Trading 4.5 | 가격 행동 신호</title>\n<style>\n:root{font-family:system-ui,-apple-system,\'Noto Sans KR\',sans-serif;color:#edf3fb;background:#0c1424}*{box-sizing:border-box}body{margin:0}main{max-width:820px;margin:auto;padding:18px 14px 46px}header{padding:8px 0 22px}.brand{font-size:23px;font-weight:800}.brand span{font-weight:400;color:#9ab1d3}.muted,small{color:#9baec9}small{font-size:12px}h1{font-size:26px;margin:0 0 10px}h2{font-size:20px;margin:0}.panel,.item{background:#15263c;border:1px solid #30465f;border-radius:18px;padding:18px;margin-bottom:15px}.panel p,.item p{line-height:1.75}.controls{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}label{display:block;color:#a6b8d0;font-size:13px}select,input{display:block;width:100%;margin-top:7px;background:#0c192c;color:#f2f6fc;border:1px solid #425772;border-radius:10px;padding:12px;font-size:15px}button{border:0;border-radius:12px;padding:13px 15px;background:#13b7aa;color:#071a23;font-size:15px;font-weight:800;cursor:pointer}button:disabled{opacity:.5;cursor:wait}.actions{display:flex;gap:8px}.actions button:first-child{flex:1}.secondary{background:#31435b;color:#edf3fb}.searchrow{display:flex;gap:8px;align-items:end}.searchrow label{flex:1}.searchrow button{height:45px}.status{font-size:13px;color:#c4d5e8;min-height:20px}.progress{height:7px;background:#293a52;border-radius:8px;overflow:hidden}.progress>div{height:100%;width:0;background:#13b7aa;transition:width .2s}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:15px 0 24px}.summary>div{background:#18263d;padding:15px 11px;border-radius:12px}.summary span{font-size:12px;color:#a6b8d0;display:block}.summary strong{display:block;font-size:22px;margin-top:7px}.heading{display:flex;align-items:center;justify-content:space-between;margin:20px 0 14px}.heading select{width:125px;margin:0}.top{display:flex;justify-content:space-between;gap:10px;align-items:start}.top strong{font-size:20px}.top small{display:block;margin-top:5px}.signal{border-radius:9px;padding:8px;font-size:12px;font-weight:800;white-space:nowrap}.long{background:#125047;color:#6ce3c6}.short{background:#57313d;color:#ffb3b3}.wait{background:#344156;color:#e0e7f0}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:18px 0}.metrics div{font-size:12px;color:#9eafc8}.metrics strong{display:block;font-size:16px;color:#edf3fb;margin-top:5px}.section{border-top:1px solid #354960;padding-top:12px;margin-top:14px}.section h3{font-size:16px;margin:0 0 7px}.section p{margin:7px 0}.tag{display:inline-block;background:#293e58;color:#e5edf7;border-radius:7px;padding:5px 8px;margin:3px 5px 3px 0;font-size:12px}.position-alert{background:#4b3528;border:1px solid #a97b46;border-radius:10px;padding:10px 12px;margin:12px 0;color:#ffe0a7;font-weight:700}.position-ok{color:#b9d0e5;font-size:13px}.warning{color:#ffd99d}.good{color:#7ce2c5}.bad{color:#ffb2b2}.empty{padding:30px;text-align:center;border:1px dashed #42536b;border-radius:14px;color:#b4c3d8}details{margin-top:12px;border-top:1px solid #354960;padding-top:12px}summary{cursor:pointer;font-weight:700}.prices{width:100%;border-collapse:collapse;font-size:13px}.prices td{padding:8px 5px;border-bottom:1px solid #2c4058}.prices td:last-child{text-align:right;font-variant-numeric:tabular-nums}footer{font-size:12px;color:#a2b3c9;line-height:1.8;margin-top:24px}@media(max-width:440px){.controls{grid-template-columns:1fr}.panel,.item{padding:15px}.top strong{font-size:17px}.signal{font-size:11px}}\n .position-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.position-grid label{font-size:12px}.calc-output{margin-top:14px;padding:14px;border:1px solid #415773;border-radius:12px;line-height:1.75}.calc-output p{margin:7px 0}.calc-note{color:#ffd99d;font-size:13px}@media(max-width:440px){.position-grid{grid-template-columns:1fr}}\n</style></head><body><main><header><div class="brand">🌊 BADANG <span>Trading</span></div><small>롱·숏 분석 · 한글 해설 · 개별 코인 검색</small></header>\n<section class="panel"><h1>롱·숏 신호 스캐너</h1><p class="muted">자동 종목 스캔 또는 원하는 USDT 선물 코인을 직접 검색할 수 있어요.</p><div class="controls"><label>분석 모드<select id="mode"><option value="scalp">단타 · 15분 / 30분 / 1시간</option><option value="swing">스윙 · 1시간 / 4시간 / 일봉</option></select></label><label>자동 분석 범위<select id="limit"><option value="5">상위 5종목</option><option value="20" selected>상위 20종목</option><option value="50">상위 50종목</option><option value="0">전체 종목 (오래 걸림)</option></select></label></div><div class="actions"><button id="scan">자동 종목 스캔 시작</button><button id="stop" class="secondary" disabled>중지</button></div><div class="section"><h3>개별 코인 검색</h3><div class="searchrow"><label>코인 이름 또는 거래쌍<input id="symbol" placeholder="예: XRP, SUI, BTCUSDT" maxlength="30" autocomplete="off" spellcheck="false"></label><button id="single">분석하기</button></div><small>Bitget·OKX의 USDT 선물 데이터 조회를 시도합니다. 상장되지 않은 종목은 오류로 안내합니다.</small></div><p id="status" class="status" role="status">분석을 시작할 수 있습니다.</p><div class="progress"><div id="bar"></div></div></section>\n\n<section class="summary"><div><span>분석 성공</span><strong id="count">—</strong></div><div><span>롱 후보</span><strong id="longCount">—</strong></div><div><span>숏 후보</span><strong id="shortCount">—</strong></div></section><section><div class="heading"><h2>분석 결과</h2><select id="filter"><option value="ALL">전체</option><option value="LONG">롱 후보</option><option value="SHORT">숏 후보</option><option value="WAIT">관망</option><option value="CHASE">추격 주의</option></select></div><div id="results"><div class="empty">스캔 또는 코인 검색을 시작하세요.</div></div></section><footer>⚠ 기술적 점수는 승률이 아닙니다. 진입가·손절가·목표가는 수수료와 슬리피지를 반영하지 않은 참고 시나리오입니다. CVD 수집 표본은 전체 시장 체결이 아닐 수 있습니다. 자동 주문 기능은 없습니다.</footer></main>\n<script>\n\'use strict\';\nconst $=id=>document.getElementById(id), n=(v,d=5)=>v===null||v===undefined||v===\'\'||!Number.isFinite(Number(v))?\'자료 없음\':Number(v).toLocaleString(\'ko-KR\',{maximumFractionDigits:d});\nconst e=v=>String(v??\'\').replace(/[&<>"\']/g,c=>({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',\'"\':\'&quot;\',"\'":\'&#39;\'}[c]));\nlet items=[],running=false,cancel=false,controller=null;\nconst why={\'TIMEFRAMES_NOT_ALIGNED\':\'15분·30분·1시간(또는 스윙 시간봉)의 추세가 한 방향으로 일치하지 않습니다.\',\'TECHNICAL_SCORE_BELOW_80\':\'기술적 평가 점수가 후보 선정 기준인 80점에 미달합니다.\',\'INVALID_PLAN_OR_RISK_REWARD_BELOW_1_5\':\'손절·목표가 시나리오가 유효하지 않거나 손익비 조건을 충족하지 못했습니다.\',\'OPPOSING_RECENT_TRADE_SAMPLE\':\'최근 수집된 체결 흐름이 기술적 방향과 충돌합니다.\',\'INVALID_TRADE_PLAN\':\'진입·손절·목표가 계산을 재검토해야 합니다.\'};\nconst reason={\'EMA bearish alignment\':\'이동평균선이 하락 방향으로 정렬됨\',\'EMA bullish alignment\':\'이동평균선이 상승 방향으로 정렬됨\',\'EMA20 below EMA50\':\'단기 이동평균선이 중기선보다 낮아 약세 신호\',\'EMA20 above EMA50\':\'단기 이동평균선이 중기선보다 높아 강세 신호\',\'MACD histogram falling negative\':\'MACD가 하락 압력을 시사함\',\'MACD histogram rising positive\':\'MACD가 상승 탄력을 시사함\',\'RSI bearish range\':\'RSI에서 약세가 상대적으로 우세함\',\'RSI bullish range\':\'RSI에서 강세가 상대적으로 우세함\',\'hidden bearish RSI divergence candidate\':\'숨은 하락 다이버전스 후보: 하락 추세 지속 가능성\',\'hidden bullish RSI divergence candidate\':\'숨은 상승 다이버전스 후보: 상승 추세 지속 가능성\',\'bullish RSI divergence candidate\':\'일반 상승 다이버전스 후보: 하락 압력 약화 가능성\',\'bearish RSI divergence candidate\':\'일반 하락 다이버전스 후보: 상승 탄력 약화 가능성\',\'rising volume with red candle\':\'음봉 거래량 증가: 매도 압력 주의\',\'rising volume with green candle\':\'양봉 거래량 증가: 매수세 유입 가능성\'};\nconst tr=t=>t===\'UP\'?\'상승\':t===\'DOWN\'?\'하락\':\'중립\';\nconst dir=x=>x.recommendation===\'LONG\'?\'LONG\':x.recommendation===\'SHORT\'?\'SHORT\':\'WAIT\';\nconst side=x=>x.technical_side===\'SHORT\'||x.candidate_side===\'SHORT\'?\'SHORT\':\'LONG\';\nconst sideKo=s=>s===\'LONG\'?\'롱(상승)\':s===\'SHORT\'?\'숏(하락)\':\'관망\';\n\nfunction locationFlag(x){\n const v=x.structure_levels||{}, lo=Number(v.support_reference), hi=Number(v.resistance_reference), price=Number(x.entry_reference);\n if(v.status!==\'AVAILABLE\'||!Number.isFinite(lo)||!Number.isFinite(hi)||!Number.isFinite(price)||hi<=lo||price<=0)return {kind:\'UNKNOWN\',label:\'가격 위치 자료 부족\',pct:null};\n const pct=(price-lo)/(hi-lo)*100, d=dir(x);\n // 후보 추천 방향만 검사: 관망의 임시 기술 방향은 추격 경고로 단정하지 않음.\n if(d===\'SHORT\'&&pct>=0&&pct<=20)return {kind:\'CHASE\',label:\'추격 숏 주의\',pct};\n if(d===\'LONG\'&&pct>=80&&pct<=100)return {kind:\'CHASE\',label:\'추격 롱 주의\',pct};\n if(pct<0||pct>100)return {kind:\'BREAK\',label:\'범위 이탈 · 돌파 확인 필요\',pct};\n return {kind:\'NORMAL\',label:\'관찰 범위 내 · 위치 추가 검토\',pct};\n}\nfunction locationBanner(x){\n const v=locationFlag(x);\n if(v.kind===\'CHASE\')return `<div class="position-alert">⚠ ${e(v.label)} · 관찰 범위 ${n(v.pct,1)}% 지점<br><small>기술적 점수가 높아도 진입 위치가 불리할 수 있습니다. 반등·되돌림과 실시간 호가를 확인하세요.</small></div>`;\n if(v.kind===\'BREAK\')return `<p class="warning"><b>가격 위치:</b> ${e(v.label)} (${n(v.pct,1)}%) · 종가 돌파와 재시험은 확인되지 않았습니다.</p>`;\n return `<p class="position-ok"><b>가격 위치:</b> ${e(v.label)}${v.pct===null?\'\':` (${n(v.pct,1)}%)`} · 진입 허가가 아닙니다.</p>`;\n}\n\nfunction divergence(x){let ds=x.divergence_details?.length?x.divergence_details:x.divergences||[];if(!ds.length)return \'뚜렷한 RSI 다이버전스가 감지되지 않았습니다. 이것만으로 상승이나 하락을 단정할 수는 없습니다.\';return ds.map(d=>{const type=typeof d===\'string\'?d:d.type||\'\';const hidden=type.includes(\'hidden\'),bull=type.includes(\'bullish\');return `${hidden?\'숨은 \':\'일반 \'}${bull?\'상승\':\'하락\'} 다이버전스${d.confirmed?\'(패턴 확인)\':\'(후보)\'}: ${bull?(hidden?\'상승 추세가 이어질 가능성을 살펴봅니다.\':\'가격 하락에 비해 RSI가 강해져 하락 압력이 약해질 가능성을 살펴봅니다.\'):(hidden?\'하락 추세가 이어질 가능성을 살펴봅니다.\':\'가격 상승에 비해 RSI가 약해져 상승 탄력이 줄어들 가능성을 살펴봅니다.\')} 다이버전스만으로 반전이 확정되지는 않습니다.`}).join(\' \')}\nfunction wave(x){\n const multi=x.wave_by_timeframe_32||{};\n const order=x.mode===\'swing\'?[\'1D\',\'4H\',\'1H\']:[\'1H\',\'30m\',\'15m\'];\n const names={\'5-wave impulse candidate\':\'5파동 추진파 후보\',\'ABC correction candidate\':\'ABC 조정 후보\'};\n const fmtTime=v=>{\n   const n=Number(v);\n   if(!Number.isFinite(n)||n<=0)return \'시각 확인 불가\';\n   const ms=n>1e12?n:n>1e9?n*1000:NaN;\n   return Number.isFinite(ms)?new Date(ms).toLocaleString(\'ko-KR\',{timeZone:\'Asia/Seoul\',month:\'numeric\',day:\'numeric\',hour:\'2-digit\',minute:\'2-digit\'}):\'시각 확인 불가\';\n };\n function renderCandidate(w,tf){\n   const pts=Array.isArray(w.pivot_points)?w.pivot_points:[];\n   if(pts.length<4)return \'<p class="muted">전환점 정보 부족</p>\';\n   const values=pts.map(p=>Number(p.price));\n   if(!values.every(Number.isFinite))return \'<p class="muted">전환점 가격 확인 불가</p>\';\n   const low=Math.min(...values),high=Math.max(...values),span=Math.max(high-low,1e-9);\n   const indices=pts.map(p=>Number(p.bar_index));\n   const xmin=Math.min(...indices),xmax=Math.max(...indices),dx=Math.max(1,xmax-xmin);\n   const coords=pts.map((p,i)=>({x:20+(indices[i]-xmin)/dx*300,y:150-(values[i]-low)/span*105,v:values[i]}));\n   const labels=w.pattern===\'5-wave impulse candidate\'?[\'시작\',\'1파\',\'2파\',\'3파\',\'4파\',\'5파\']:[\'시작\',\'A\',\'B\',\'C\'];\n   const path=coords.map(p=>`${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(\' \');\n   const graphic=`<svg viewBox="0 0 340 182" role="img" aria-label="${e(tf)}의 자동 파동 전환점" style="width:100%;max-width:520px;background:#101f32;border-radius:10px"><polyline points="${path}" fill="none" stroke="#8bbcf0" stroke-width="3"/>${coords.map((p,i)=>`<circle cx="${p.x}" cy="${p.y}" r="4" fill="#f6c47b"/><text x="${p.x}" y="${Math.max(13,p.y-12)}" text-anchor="middle" font-size="10" fill="#fff">${labels[i]||\'\'}</text><text x="${p.x}" y="${Math.min(174,p.y+20)}" text-anchor="middle" font-size="9" fill="#b9cde4">${n(p.v,2)}</text>`).join(\'\')}</svg>`;\n   const rows=pts.map((p,i)=>`<tr><td>${labels[i]||i}</td><td>${n(p.price,5)} USDT</td><td>${e(fmtTime(p.candle_time))}</td></tr>`).join(\'\');\n   const elapsed=w.bars_since_last_pivot;\n   const rel=w.higher_relation;\n   const cm=w.cross_tf_metrics||{};\n   const cmp=w.cross_tf_comparison;\n   const comparison=cmp===\'LIKELY_SAME_MOVE\'?\'상위 시간봉과 같은 가격 움직임일 가능성 — 독립적인 파동 확인이 아님\':cmp===\'OVERLAPPING_UNCONFIRMED\'?\'시간이 일부 겹치지만 같은 파동인지 불확실\':cmp===\'SEPARATE_TIME_WINDOWS\'?\'관찰 시기가 다른 별개 움직임\': \'비교 가능한 상위 후보 없음\';\n   const detail=cm.time_overlap==null?\'\':` · 시간 겹침 ${n(cm.time_overlap*100,1)}% · 가격대 겹침 ${n(cm.price_overlap*100,1)}%`;\n   const relation=rel===\'TIME_WINDOW_CONTAINED\'?\'상위 후보의 시간 범위 안에 있음 (파동 포함 검증 아님)\':rel===\'DIFFERENT_TIME_WINDOW\'?\'상위 후보와 시간 범위가 다름 — 별개 파동으로 취급\':rel===\'NO_CURRENT_PARENT\'?\'상위 시간봉에 최근 후보 없음 — 하위 파동 단독 후보\':\'상위 시간봉 관계 확인 전\';\n   const conf=w.confluence_36||{}, fb=conf.fib||{}, vol=conf.volume||{}, rules=conf.impulse_rules_38||{};\n   const proof=w.evidence_44||{};\n   const proofTitle=proof.status===\'STRUCTURE_CONFLICT\'?\'구조 충돌 · 신뢰하기 어려움\':proof.status===\'PARTIAL_EVIDENCE\'?\'일부 근거 있음 · 미확정\':\'근거 부족 · 미확정\';\n   const proofLine=`<div class="section"><p><b>파동 검증 (4.4): ${e(proofTitle)}</b></p><p>${(proof.supports||[]).map(z=>\'✓ \'+e(z)).join(\' · \')||\'확인된 보조 근거 없음\'}</p>${(proof.conflicts||[]).length?`<p class="warning">구조 충돌: ${(proof.conflicts||[]).map(e).join(\' · \')}</p>`:\'\'}<p class="muted">아직 확인 안 된 것: ${(proof.unverified||[]).map(e).join(\' · \')||\'추가 검증 필요\'}</p><p class="muted">파동 완료·추세 반전·매수/매도 시점은 확인되지 않았습니다.</p></div>`;\n   const temporal=w.temporal_relation_39||{};\n   const temporalLine=`<p><b>파동 시간 관계 (3.9):</b> ${e(temporal.note||\'시간 관계 자료 없음\')}${temporal.parent_end_time?`<small> · 상위 후보 마지막 전환점 ${e(fmtTime(temporal.parent_end_time))} · 하위 후보 시작 ${e(fmtTime(temporal.child_start_time))}</small>`:\'\'}</p>`;\n\n   // 3.7: evidence summary, not a numerical success probability. Never treat unverified flow as confirmation.\n   const evidence=[];\n   let supporting=0, conflicts=0, missing=0;\n   if(w.pattern===\'5-wave impulse candidate\'){\n     if(rules.status===\'CONFLICT\'){\n       evidence.push(\'파동 기본 규칙 충돌: \'+(rules.failures||[]).join(\' · \')+\' — 일반적인 5파 추진파로 인정하기 어려움\');\n       conflicts++;\n     }else if(rules.status===\'BASIC_RULES_PASS\'){\n       evidence.push(\'파동 기본 규칙: 명백한 구조 위반은 발견되지 않음 (시작점의 타당성·완료 여부는 미확인)\');\n     }else{evidence.push(\'파동 기본 규칙: 확인 자료 부족\');missing++;}\n   }\n   if(fb.status===\'AVAILABLE\' && w.pattern===\'5-wave impulse candidate\'){\n     const r2=Number(fb.wave2_retracement),r4=Number(fb.wave4_retracement),r3=Number(fb.wave3_to_wave1);\n     if([r2,r4,r3].every(Number.isFinite)){\n       if(r2>=1 || r4>=1 || r3<=0){evidence.push(\'피보나치: 기본 파동 구조와 충돌하는 비율이 있어 재검토 필요\');conflicts++;}\n       else if(r2>0.85){evidence.push(\'피보나치: 2파 되돌림이 깊어 파동 시작점과 구분을 재확인해야 함\');conflicts++;}\n       else {evidence.push(\'피보나치: 주요 되돌림·길이 비율이 기본 구조와 크게 충돌하지 않음\');supporting++;}\n     }else{evidence.push(\'피보나치: 일부 검증 수치 부족\');missing++;}\n   }else{evidence.push(\'피보나치: 검증 가능한 파동 비율 부족\');missing++;}\n   const vr=vol.wave5_vs_wave3_ratio==null?null:Number(vol.wave5_vs_wave3_ratio);\n   if(vr!==null && Number.isFinite(vr) && vr>=0){\n     if(vr<0.85){evidence.push(\'거래량: 5파 구간의 거래량 감소 — 힘이 약해졌을 가능성, 종료 확정은 아님\');supporting++;}\n     else{evidence.push(\'거래량: 5파 구간 거래량이 유지·증가 — 파동 종료 근거로 보기 어려움\');}\n   }else{evidence.push(\'거래량: 파동 구간 비교 자료 부족\');missing++;}\n   if(cmp===\'LIKELY_SAME_MOVE\'){evidence.push(\'상위 시간봉: 같은 가격 움직임과 중복 가능 — 독립 확인으로 계산하지 않음\');missing++;}\n   else if(cmp===\'OVERLAPPING_UNCONFIRMED\'){evidence.push(\'상위 시간봉: 시간대가 겹치지만 구조 확인 부족\');missing++;}\n   else if(cmp===\'SEPARATE_TIME_WINDOWS\'){evidence.push(\'상위 시간봉: 서로 다른 시기의 움직임 — 교차 확인 불가\');missing++;}\n   else{evidence.push(\'상위 시간봉: 비교 가능한 최근 후보 없음\');missing++;}\n   evidence.push(\'OI·펀딩비·CVD: 파동 구간과 거래소·시각 일치 미검증 — 확증 근거에서 제외\');missing++;\n   const level=conflicts?\'구조 충돌 · 재검토 필요\':missing>=2?\'근거 부족 · 추가 확인 필요\':\'부분적 근거\';\n   const confluenceDetail=`<p><b>다른 지표와 함께 본 파동 판단 (3.9): ${e(level)}</b></p><p class="muted">${e(w.direction===\'down\'?\'하락\':\'상승\')} 파동 후보는 발견됐지만, 이 결과만으로 5파 완료나 추세 전환을 확인할 수 없습니다.</p><p>${evidence.map(v=>\'• \'+v).join(\'<br>\')}</p><p class="muted">피보나치 계산과 거래량은 내부 검증에 사용합니다. 위 항목은 독립된 증거가 아니므로 단순 합산하거나 승률로 환산하지 않습니다.</p>${(conf.warnings||[]).map(z=>`<p class="warning">${e(z)}</p>`).join(\'\')}`;\n   return `<p><b>${e(w.direction===\'down\'?\'하락\':\'상승\')} ${e(names[w.pattern]||\'파동 후보\')}</b> · 전환점 반경 ${n(w.radius,0)}캔들 · 형태 적합도 ${e(w.confidence===\'medium\'?\'보통\':\'낮음\')}</p><p class="muted">상위 시간봉 관계: ${e(comparison)}${detail}<br><small>${e(relation)}${w.higher_direction_agrees===false?" · 방향도 다름":""}</small></p>${graphic}${proofLine}${temporalLine}${confluenceDetail}<table class="prices"><tr><td>전환점</td><td>가격</td><td>시각 (한국)</td></tr>${rows}</table><p class="muted">마지막 확인 전환점 이후 ${elapsed==null?\'자료 없음\':n(elapsed,0)+\'개\'} 완료 캔들이 경과했습니다. 마지막 점은 현재 가격이 아니며, 파동 완료 여부는 확인되지 않았습니다.</p>`;\n }\n let sections=order.map((tf,i)=>{\n   const v=multi[tf];\n   if(!v)return `<p>${e(tf)}: 분석 자료 없음</p>`;\n   if(v.status!==\'AVAILABLE\')return `<p>${e(tf)}: ${v.status===\'INSUFFICIENT_DATA\'?\'완료 캔들 부족\':\'분석 불가\'}</p>`;\n   const broad=((v.views||[]).find(z=>z.radius===6)?.candidates||[]).filter(w=>w.age_class===\'RECENT\');\n   const narrow=((v.views||[]).find(z=>z.radius===3)?.candidates||[]).filter(w=>w.age_class===\'RECENT\');\n   const chosen=broad.length?broad:narrow;\n   const label=broad.length?\'넓은 전환점 기준\':\'짧은 전환점 기준\';\n   const headline=chosen.length?chosen.map(w=>`${w.direction===\'down\'?\'하락\':\'상승\'} ${names[w.pattern]||\'후보\'}`).join(\' / \'):\'최근 파동 후보 없음\';\n   return `<div class="section"><p><b>${e(tf)} ${i===0?\'· 상위 기준봉\':\'\'}</b> — ${e(headline)} ${chosen.length?\'(\'+label+\')\':\'\'}</p>${chosen.length?chosen.map(w=>renderCandidate(w,tf)).join(\'\'):\'<p class="muted">현재 자동 규칙으로는 파동을 특정하지 않습니다. 실제 파동이 없다는 뜻은 아닙니다.</p>\'}${!broad.length&&narrow.length?\'<p class="warning">⚠ 넓은 전환점 기준에서는 후보가 확인되지 않았습니다. 짧은 파동을 전체 5파로 단정하면 안 됩니다.</p>\':\'\'}</div>`;\n }).join(\'\');\n return `<p><b>엘리엇파동 종합 검증 (3.9)</b></p><p class="muted">최근 후보의 실제 전환점 시각으로 선후관계와 시간 겹침을 비교합니다. 시각 관계만으로 파동 포함관계나 반전을 확정하지 않습니다. 5파 후보는 기본 추진파 규칙을 다시 확인하지만 파동 시작점·상하위 포함 관계·5파 완료·ABC·WXY는 확정하지 않습니다.</p>${sections}`;\n}\nfunction fib(x){const f=x.fibonacci||{};const labels=[[\'retracement_382\',\'38.2% 되돌림\'],[\'retracement_500\',\'50% 되돌림\'],[\'retracement_618\',\'61.8% 되돌림\'],[\'extension_1272_up\',\'상승 확장 참고가\'],[\'extension_1272_down\',\'하락 확장 참고가\']];const rows=labels.filter(([k])=>Number.isFinite(Number(f[k]))&&f[k]!=null).map(([k,l])=>`<tr><td>${l}</td><td>${n(f[k],8)} USDT</td></tr>`).join(\'\');return rows?`<p>이 가격들은 과거 변동폭으로 계산한 <b>잠재적 지지·저항 참고 구간</b>입니다. 가격이 반드시 여기에서 반등하거나 멈추는 것은 아닙니다.</p><table class="prices">${rows}</table>`:\'<p>계산 가능한 피보나치 구간이 없습니다.</p>\'}\nfunction interpretation(x){const t=Object.entries(x.timeframe_trends||{});const ups=t.filter(([,v])=>v===\'UP\').length,downs=t.filter(([,v])=>v===\'DOWN\').length;const direction=ups===t.length&&t.length?\'모든 분석 시간봉이 상승 방향입니다.\':downs===t.length&&t.length?\'모든 분석 시간봉이 하락 방향입니다.\':\'시간봉별 방향이 서로 다릅니다. 짧은 반등과 큰 추세가 충돌할 수 있습니다.\';const lean=side(x),trendOpposes=(lean===\'LONG\'&&downs===t.length&&t.length)||(lean===\'SHORT\'&&ups===t.length&&t.length);const conflict=trendOpposes?\'현재 시간봉의 공통 추세와 기술적 우세 방향이 반대입니다. 이는 추세 전환이 확정됐다는 뜻이 아니라 반등·되돌림 가능성을 나타내는 지표가 일부 우세하다는 의미입니다. 추세 전환 확인 전에는 역추세 진입에 특히 주의해야 합니다. \':\'\';const score=Math.max(x.long_score||0,x.short_score||0);const r=x.rsi;const rsi=r==null?\'RSI 자료가 없습니다.\':r>=70?\'RSI \'+n(r,2)+\'로 매수세가 과열됐을 가능성을 살펴봐야 합니다.\':r<=30?\'RSI \'+n(r,2)+\'로 매도세가 과도했을 가능성을 살펴봐야 합니다.\':\'RSI \'+n(r,2)+\'로 극단적 과매수·과매도 구간은 아닙니다.\';return `${direction} ${conflict}${rsi} 기술적 평가에서는 ${sideKo(side(x))} 방향이 상대적으로 우세하며 점수는 ${n(score,0)}점입니다. 점수는 성공 확률이 아닙니다.`}\nfunction entryChecklist(x){const t=Object.entries(x.timeframe_trends||{}),s=side(x),desired=s===\'LONG\'?\'UP\':\'DOWN\',missing=t.filter(([,v])=>v!==desired).map(([k])=>k);const score=x.technical_score??Math.max(x.long_score||0,x.short_score||0);const parts=[];if(missing.length)parts.push(missing.map(e).join(\'·\')+\' 시간봉에서 \'+(s===\'LONG\'?\'상승\':\'하락\')+\' 추세 확인 필요\');if(score<80)parts.push(\'기술적 평가가 80점 이상으로 개선되는지 확인\');if((x.entry_blockers||[]).includes(\'INVALID_PLAN_OR_RISK_REWARD_BELOW_1_5\'))parts.push(\'손절·목표가 및 손익비 시나리오 재검증\');parts.push(\'실제 거래소 호가·유동성·가격 최신성 확인\');return \'<p>\'+parts.map(e).join(\' · \')+\'</p><p class="muted">이 항목들은 재검토 조건이며 충족되더라도 자동 진입 허가가 아닙니다.</p>\'} \n\nfunction candleTime(value){\n const v=Number(value);\n if(!Number.isFinite(v)||v<=0)return \'시각 자료 없음\';\n const ms=v>1e12?v:v>1e9?v*1000:NaN;\n if(!Number.isFinite(ms))return \'시각 형식 확인 필요\';\n return new Date(ms).toLocaleString(\'ko-KR\',{timeZone:\'Asia/Seoul\',month:\'numeric\',day:\'numeric\',hour:\'2-digit\',minute:\'2-digit\'});\n}\nfunction breakoutReview(x){\n const v=x.breakout_retest_27||{};\n if(v.status!==\'AVAILABLE\')return `<p class="warning">분석 불가: ${e(v.reason||\'자료 부족\')}</p>`;\n if(v.stage===\'NO_BREAKOUT\')return \'<p>최근 완료된 캔들 6개에서 신규 종가 돌파가 관찰되지 않았습니다.</p>\';\n const labels={BREAKOUT_OBSERVED:\'① 돌파 관찰\',AWAIT_RETEST:\'② 재시험 대기\',RETEST_CANDIDATE:\'③ 재시험 반응 후보\',INVALIDATED:\'돌파 무효화 가능성\'};\n const idx=v.stage===\'RETEST_CANDIDATE\'?2:v.stage===\'AWAIT_RETEST\'?1:0;\n const steps=[\'① 돌파 관찰\',\'② 재시험 대기\',\'③ 재시험 반응 후보\'];\n const timeline=`<div style="display:flex;gap:6px;flex-wrap:wrap;margin:10px 0">${steps.map((t,i)=>`<span style="border-radius:7px;padding:6px 9px;background:${i<=idx?\'#28516b\':\'#29384b\'};color:${i<=idx?\'#e3f7ff\':\'#9aadc1\'};font-size:12px">${t}</span>`).join(\'\')}</div>`;\n const hold=v.currently_beyond_level===true?\'기준선 바깥 유지\':v.currently_beyond_level===false?\'기준선 안쪽 복귀\':\'확인 불가\';\n const age=v.bars_since_retest;\n const ageWarning=age!=null&&age>=3?\'⚠ 재시험 이후 완료된 캔들이 3개 이상 경과했습니다. 오래된 신호일 수 있습니다.\':\'\';\n const ratio=v.breakout_volume_ratio==null?\'비교 불가\':n(v.breakout_volume_ratio,2)+\'배\';\n return `<p><b>현재 관찰 단계:</b> ${e(labels[v.stage]||\'확인 불가\')}</p>${timeline}<p><b>돌파 방향:</b> ${v.direction===\'UP\'?\'상단 돌파\':\'하단 이탈\'} · <b>기준선:</b> ${n(v.level,8)} USDT (이전 ${n(v.reference_lookback||20,0)}개 캔들)</p><p><b>돌파 관찰 시각:</b> ${e(candleTime(v.breakout_time))} · <b>돌파 후:</b> ${n(v.bars_since_breakout||0,0)}개 완료 캔들</p><p><b>재시험 후보:</b> ${v.retest_price==null?\'아직 관찰되지 않음\':`${n(v.retest_price,8)} USDT · ${e(candleTime(v.retest_time))} · 이후 ${n(age,0)}개 완료 캔들 경과`}</p><p><b>최신 완료 캔들:</b> ${v.latest_closed_price==null?\'자료 없음\':n(v.latest_closed_price,8)+\' USDT\'} · ${e(hold)}</p><p><b>돌파 거래량:</b> 이전 20개 평균의 ${ratio}</p>${ageWarning?`<p class="warning">${ageWarning}</p>`:\'\'}${v.stage===\'INVALIDATED\'?\'<p class="warning">돌파 후 반대 방향 종가가 관찰되어 과거 재시험 후보를 현재 유효한 신호로 해석하면 안 됩니다.</p>\':\'\'}<p class="muted">재시험 허용 폭 0.25%는 설명용 기준입니다. 완료된 캔들만 사용하며 40개 캔들 가격 위치 분석과 기준선이 다를 수 있습니다. 이 분석은 주문 신호가 아닙니다.</p>`;\n}\nfunction structureReview(x){\n const v=x.structure_levels||{};\n if(v.status!==\'AVAILABLE\')return `<p class="warning">가격 구조 분석 자료 부족: ${e(v.reason||\'이전 캔들 확인 불가\')}</p>`;\n const lo=Number(v.support_reference),hi=Number(v.resistance_reference),price=Number(x.entry_reference);\n if(!Number.isFinite(lo)||!Number.isFinite(hi)||!Number.isFinite(price)||hi<=lo)return \'<p class="warning">가격 구조 계산에 필요한 값이 올바르지 않습니다.</p>\';\n const pct=(price-lo)/(hi-lo)*100;\n const loc=pct<0?\'범위 하단 아래\':pct>100?\'범위 상단 위\':pct<=20?\'하단 근접\':pct>=80?\'상단 근접\':\'범위 중간\';\n const s=side(x),caution=[];\n if(s===\'SHORT\'&&pct<=20&&pct>=0)caution.push(\'숏 후보이지만 이전 범위 하단에 가까워 추격 숏과 단기 반등에 주의\');\n if(s===\'LONG\'&&pct>=80&&pct<=100)caution.push(\'롱 후보이지만 이전 범위 상단에 가까워 추격 롱과 되돌림에 주의\');\n if(pct<0)caution.push(\'이전 하단 아래: 이탈이 관찰되지만 종가 확정·재시험은 검증되지 않음\');\n if(pct>100)caution.push(\'이전 상단 위: 돌파가 관찰되지만 종가 확정·재시험은 검증되지 않음\');\n const stop=Number(x.stop_loss),tp1=Number(x.take_profit_1);\n if(Number.isFinite(stop)&&Number.isFinite(tp1)){\n  if(s===\'SHORT\'&&tp1<lo)caution.push(\'1차 목표가가 이전 범위 하단 아래: 하단 이탈 후 추가 하락이 필요할 수 있음\');\n  if(s===\'LONG\'&&tp1>hi)caution.push(\'1차 목표가가 이전 범위 상단 위: 상단 돌파 후 추가 상승이 필요할 수 있음\');\n }\n const position=Math.max(0,Math.min(100,pct));\n return `<p><b>현재 위치:</b> ${e(loc)} · 범위 내 상대 위치 ${n(pct,1)}% (하단 0%, 상단 100%)</p><div style="height:10px;background:#30435a;border-radius:8px;position:relative;margin:16px 3px 10px"><div style="position:absolute;left:${position}%;top:-4px;width:8px;height:18px;background:#6ce3c6;border-radius:4px;transform:translateX(-50%)"></div></div><table class="prices"><tr><td>이전 캔들 최저가 (하단 참고)</td><td>${n(lo,8)} USDT</td></tr><tr><td>이전 캔들 최고가 (상단 참고)</td><td>${n(hi,8)} USDT</td></tr><tr><td>관찰 범위 폭 / 기준가</td><td>${n(v.range_width_pct,2)}%</td></tr><tr><td>분석에 사용한 이전 캔들</td><td>${n(v.lookback_used,0)}개</td></tr></table>${caution.length?`<p class="warning"><b>진입 위치 점검:</b> ${caution.map(e).join(\' · \')}</p>`:\'<p>관찰 범위 기준으로 특별한 추격 경고는 없지만 진입을 승인하는 의미는 아닙니다.</p>\'}<p class="muted">상대 위치 20%·80%는 설명용 경계이며 검증된 지지·저항이나 매매 신호가 아닙니다. 범위 밖의 위치는 0% 미만 또는 100% 초과로 표시됩니다. 종가 돌파·재시험 성공은 별도 검증되지 않았습니다. 기존 점수·진입가·손절가·목표가는 변경하지 않았습니다.</p>`;\n}\nfunction entryRiskReview(x){\n const sideName=side(x), entry=Number(x.entry_reference), stop=Number(x.stop_loss), tp1=Number(x.take_profit_1), tp2=Number(x.take_profit_2);\n const valid=[entry,stop,tp1,tp2].every(v=>Number.isFinite(v)&&v>0) && (sideName===\'LONG\'?stop<entry&&entry<tp1&&tp1<tp2:tp2<tp1&&tp1<entry&&entry<stop);\n if(!valid)return \'<p class="warning">진입·손절·목표가 순서가 유효하지 않아 위험을 계산할 수 없습니다. 가격을 임의로 추정하지 않습니다.</p>\';\n const risk=Math.abs(entry-stop), riskPct=100*risk/entry, reward1=Math.abs(tp1-entry), reward2=Math.abs(tp2-entry), rr1=reward1/risk, rr2=reward2/risk;\n const t=Object.values(x.timeframe_trends||{}), expected=sideName===\'LONG\'?\'UP\':\'DOWN\', aligned=t.length>0&&t.every(v=>v===expected);\n const score=Number(x.technical_score??Math.max(x.long_score||0,x.short_score||0));\n const quality=x.data_quality||{}, caveats=x.data_caveats||[];\n const flags=[];\n if(!aligned)flags.push(\'분석 시간봉이 기술적 우세 방향과 모두 일치하지 않음\');\n if(!Number.isFinite(score)||score<80)flags.push(\'기술적 점수가 후보 기준 80점 미만\');\n if(rr1<1.5)flags.push(\'1차 목표 손익비가 1.5:1 미만\');\n if(riskPct>=5)flags.push(\'손절까지의 기준가 대비 거리가 5% 이상 — 포지션 크기와 레버리지 점검\');\n if(quality.cross_exchange)flags.push(\'캔들과 파생상품 데이터의 거래소가 다름\');\n if(quality.trade_coverage!==\'CONFIRMED\')flags.push(\'체결 데이터 전체 수집이 확인되지 않음\');\n if(caveats.length)flags.push(...caveats.filter(v=>!flags.some(f=>f.includes(v))));\n const status=flags.length?\'추가 검증 필요\':\'기본 기술 조건 충족 — 실행 판단은 별도\';\n return `<p><b>진입 검토:</b> ${e(status)}</p><table class="prices"><tr><td>진입 기준가 (실시간 호가 아님)</td><td>${n(entry,8)} USDT</td></tr><tr><td>손절 기준가</td><td>${n(stop,8)} USDT</td></tr><tr><td>손절 거리 (기준가 대비)</td><td>${n(riskPct,2)}%</td></tr><tr><td>1차 목표 / 예상 손익비</td><td>${n(tp1,8)} / ${n(rr1,2)}:1</td></tr><tr><td>2차 목표 / 예상 손익비</td><td>${n(tp2,8)} / ${n(rr2,2)}:1</td></tr></table>${flags.length?`<p class="warning"><b>확인할 위험:</b> ${flags.map(e).join(\' · \')}</p>`:\'<p class="good">표시된 기술 조건에 큰 충돌은 없지만, 체결 가능성과 시장 상황은 별도로 확인해야 합니다.</p>\'}<p class="muted">손익비는 가격 차이만 계산한 값입니다. 수수료·펀딩비·슬리피지·레버리지·포지션 규모는 반영하지 않습니다. 지지·저항 돌파나 재시험이 확인됐다는 뜻도 아닙니다.</p>`;\n}\nfunction dateKo(x){if(!x.analysis_timestamp_utc)return \'분석 시각 자료 없음\';const d=new Date(x.analysis_timestamp_utc);return Number.isNaN(d.getTime())?\'분석 시각 자료 없음\':d.toLocaleString(\'ko-KR\',{timeZone:\'Asia/Seoul\',hour12:false})+\' (한국시간 · 서버 분석 시각)\'}\nfunction derivative(x){const v=x.v17_research||{},tw=v.trade_window||{},cross=x.data_quality?.cross_exchange;const oi=v.oi_change_1h_pct;let oiText=oi==null?\'미결제약정 변화 자료가 없습니다.\':`최근 1시간 미결제약정은 ${n(Math.abs(oi),3)}% ${oi>0?\'증가\':\'감소\'}했습니다. ${oi>0?\'새 포지션 유입 가능성이 있지만 롱·숏 어느 쪽인지는 OI만으로 알 수 없습니다.\':\'포지션 정리 가능성이 있지만 방향을 단정할 수 없습니다.\'}`;let funding=v.funding_rate==null?\'펀딩비 자료가 없습니다.\':`펀딩비 ${n(v.funding_rate*100,4)}%: ${v.funding_rate>0?\'일반적으로 롱 포지션이 숏에 비용을 지급하는 방향입니다.\':v.funding_rate<0?\'일반적으로 숏 포지션이 롱에 비용을 지급하는 방향입니다.\':\'롱·숏 간 펀딩 부담이 거의 없습니다.\'}`;let cvd=tw.cvd_contracts==null?\'체결 CVD 표본이 없습니다.\':`수집 표본의 CVD는 ${n(tw.cvd_contracts,3)} 계약으로 ${tw.cvd_contracts>0?\'적극적 매수가 우세했습니다.\':tw.cvd_contracts<0?\'적극적 매도가 우세했습니다.\':\'매수·매도 체결이 비슷했습니다.\'} ${tw.coverage_confirmed?\'\':\'단, 수집 공백이나 미관측 체결이 있어 전체 시장의 15분 CVD가 아닙니다.\'}`;let vwap=v.vwap?.value==null?\'캔들 기준 VWAP 근사값이 없습니다.\':`캔들 기반 VWAP 근사값은 ${n(v.vwap.value,8)} USDT입니다. ${x.entry_reference>v.vwap.value?\'현재 기준가가 이 값보다 높습니다.\':\'현재 기준가가 이 값보다 낮습니다.\'} 정확한 전체 체결 VWAP는 아닙니다.`;return `<p><b>미결제약정(OI):</b> ${oiText}</p><p><b>펀딩비:</b> ${funding}</p><p><b>체결 흐름(CVD):</b> ${cvd}</p><p><b>거래량 가중 평균가(VWAP):</b> ${vwap}</p>${cross?\'<p class="warning">⚠ 캔들과 파생상품 자료가 서로 다른 거래소에서 수집됐습니다. 수치를 같은 시장의 완전한 정보로 해석하면 안 됩니다.</p>\':\'\'}`}\nfunction reboundReview(x){\n const price=Number(x.entry_reference), data=x.wave_by_timeframe_32||{};\n const order=x.mode===\'swing\'?[\'4H\',\'1H\']:[\'30m\',\'15m\'];\n let low=null, first=null, second=null, tf=\'\', source=\'\';\n for(const k of order){\n  const w=data[k];\n  if(!w||w.pattern!==\'5-wave impulse candidate\'||!Array.isArray(w.pivot_points)||w.pivot_points.length<6)continue;\n  const p=w.pivot_points.map(z=>Number(z.price));\n  if(!p.every(z=>Number.isFinite(z)&&z>0))continue;\n  if(!(p[0]>p[1]&&p[2]>p[1]&&p[3]<p[2]&&p[4]>p[3]&&p[5]<p[4]))continue;\n  low=p[5];first=p[4];second=p[2];tf=k;source=\'최근 하락 파동 후보\';break;\n }\n if(low===null){\n  const st=x.structure_levels||{};\n  const s=Number(st.support_reference),r=Number(st.resistance_reference);\n  if(st.status===\'AVAILABLE\'&&Number.isFinite(s)&&Number.isFinite(r)&&s>0&&r>s){low=s;source=\'이전 캔들 가격 범위\';}\n }\n if(!Number.isFinite(price)||price<=0)return \'<p>현재 분석 가격을 확인할 수 없어 반등 지점을 표시하지 않습니다.</p>\';\n if(low===null)return \'<p><b>반등 가격 산정 보류</b></p><p>최근 하락 파동과 이전 캔들에서 신뢰할 만한 참고 저점을 찾지 못했습니다. 가격을 임의로 만들지 않습니다.</p>\';\n const broken=price<low;\n const recovered=first!==null&&price>first;\n const levelLabel=source===\'최근 하락 파동 후보\'?\'직전 하락 저점\':\'최근 관찰 범위의 최저가\';\n const step=first!==null?`<tr><td>② 첫 반등 확인 참고가</td><td><b>${n(first,5)} USDT</b></td></tr>`:\'\';\n const stronger=second!==null?`<tr><td>③ 추가 회복 참고가</td><td>${n(second,5)} USDT</td></tr>`:\'\';\n const state=broken?\'현재 가격이 저점 아래입니다. 이전 저점을 지지선으로 가정해 추매하면 위험합니다.\':recovered?\'첫 반등 참고 고점 위에 있지만 상승 추세가 확정된 것은 아닙니다.\':\'저점 부근에서 반등할 수 있는지 관찰하는 단계입니다. 아직 반등이 확인된 것은 아닙니다.\';\n const how=first!==null?`가격이 ${n(low,5)} 부근에서 더 내려가지 않고, 완료된 캔들에서 반등을 보인 뒤 ${n(first,5)} 위로 회복하는지 살펴보세요.`:`${n(low,5)} 부근에서 하락이 멈추는지 확인하세요. 첫 반등 확인 고점은 아직 계산할 근거가 부족합니다.`;\n return `<p><b>한눈에 보는 반등 가격</b></p><table class="prices"><tr><td>① 우선 살펴볼 가격 (${e(levelLabel)})</td><td><b>${n(low,5)} USDT</b></td></tr>${step}${stronger}<tr><td>분석 당시 가격</td><td>${n(price,5)} USDT</td></tr></table><p class="${broken?\'bad\':\'warning\'}"><b>현재 판단:</b> ${e(state)}</p><p><b>쉽게 설명하면:</b> ${e(how)}</p><p><b>추매할 때 주의할 점:</b> ${n(low,5)} 아래로 내려가면 추가 하락을 경계해야 합니다. 이 가격 자체가 매수 신호는 아닙니다. 추매하면 보유 수량과 손실 위험이 함께 커지므로 청산가와 증거금을 먼저 확인하세요.</p><p class="muted">계산 근거: ${e(source)}${tf?\' · \'+e(tf)+\'봉\':\'\'}. 모두 과거 캔들에 기반한 참고 가격이며 실시간 주문가·확정 지지선이 아닙니다. ${first===null?\'파동 고점 확인 자료가 없어 반등 확인 가격을 표시하지 않았습니다.\':\'\'}</p>`;\n}\nfunction card(x){\n const a=x.price_action_45||{}, d=x.recommendation||\'WAIT\';\n const side=d===\'LONG\'?\'롱 매수 후보\':d===\'SHORT\'?\'숏 매도 후보\':\'관찰 중\';\n const color=d===\'LONG\'?\'long\':d===\'SHORT\'?\'short\':\'wait\';\n const fmt=v=>Number.isFinite(Number(v))&&v!==null&&v!==undefined?n(v,6)+\' USDT\':\'미확인\';\n const trend=x.timeframe_trends||{};\n const times=Object.entries(trend).map(([tf,v])=>tf+\' \'+tr(v)).join(\' · \');\n const rationale=a.reason||\'가격 움직임 검증 대기\';\n const details=`<details><summary>상세 기술적 분석 보기</summary><p>기술적 롱/숏 점수: ${n(x.long_score,0)} / ${n(x.short_score,0)} (승률 아님)</p><p>엘리엇파동·피보나치·수급은 참고 근거이며 독립적인 매수 허가가 아닙니다.</p><details><summary>엘리엇파동 후보</summary><p>${wave(x)}</p></details><details><summary>피보나치 참고</summary>${fib(x)}</details><details><summary>다이버전스</summary><p>${divergence(x)}</p></details><details><summary>거래량·파생상품 자료</summary>${derivative(x)}</details><details><summary>자료 출처·한계</summary><p>캔들 ${e(x.exchange||\'미확인\')} · 분석시각 ${e(dateKo(x))}. 종가 기반 참고 신호이며 실시간 주문 호가가 아닙니다. 체결·슬리피지·수수료 및 미래 성과 미검증.</p></details></details>`;\n return `<article class="item"><div class="top"><div><strong>${e(x.symbol)}</strong><small>${e(x.exchange||\'\')} · ${e(x.mode===\'scalp\'?\'단타\':\'스윙\')} · ${e(dateKo(x))}</small></div><div class="signal ${color}">${side}</div></div><div class="section"><h3>${d===\'WAIT\'?\'아직 진입 신호 없음\':e(a.kind||\'가격 행동 신호\')+(a.countertrend?\' · 역추세 주의\':\'\')}</h3><p>${e(rationale)}</p><p class="muted">${e(times)}</p></div>${d===\'WAIT\'?`<p>최근 지지 ${fmt(a.support)} · 저항 ${fmt(a.resistance)}. 신호가 생길 때 재분석하세요.</p>`:`<div class="metrics"><div>진입 참고가<strong>${fmt(a.entry)}</strong></div><div>손절 참고가<strong>${fmt(a.stop)}</strong></div><div>1차 목표 · 1.3R<strong>${fmt(a.tp1)}</strong></div><div>2차 목표 · 1.8R<strong>${fmt(a.tp2)}</strong></div></div><p class="warning">${a.countertrend?\'상위 추세 반대 방향의 단기 후보입니다. 반전 확정 아님.\':\'확정봉 기준 후보입니다.\'} 실시간 호가·유동성·손절 가능성 확인 후 판단하세요.</p>`}${details}</article>`;\n}\nfunction render(){const f=$(\'filter\').value;const list=items.filter(x=>f===\'ALL\'||(f===\'CHASE\'?locationFlag(x).kind===\'CHASE\':dir(x)===f)).sort((a,b)=>(b.technical_score||0)-(a.technical_score||0));$(\'results\').innerHTML=list.length?list.map(card).join(\'\'):\'<div class="empty">해당 조건의 분석 결과가 없습니다.</div>\';$(\'count\').textContent=items.length;$(\'longCount\').textContent=items.filter(x=>dir(x)===\'LONG\').length;$(\'shortCount\').textContent=items.filter(x=>dir(x)===\'SHORT\').length}\nconst wait=ms=>new Promise(r=>setTimeout(r,ms));\nasync function getJSON(url,ms=45000){controller=new AbortController();const timer=setTimeout(()=>controller.abort(),ms);try{const r=await fetch(url,{cache:\'no-store\',signal:controller.signal});const j=await r.json();if(!r.ok||j.error)throw Error(j.error||`서버 오류 ${r.status}`);return j}finally{clearTimeout(timer);controller=null}}\nasync function request(url){let last;for(let attempt=1;attempt<=2&&!cancel;attempt++){try{return await getJSON(url)}catch(err){last=err;if(cancel)break;$(\'status\').textContent=`요청 ${attempt}회 실패: ${err.name===\'AbortError\'?\'응답 시간 초과\':err.message}${attempt===1?\' · 한 번 더 시도합니다.\':\'\'}`;if(attempt===1)await wait(1000)}}throw last||Error(\'분석이 중단됐습니다\')}\nfunction busy(v){running=v;$(\'scan\').disabled=v;$(\'single\').disabled=v;$(\'stop\').disabled=!v}\nasync function start(single){if(running)return;cancel=false;items=[];render();$(\'bar\').style.width=\'0%\';busy(true);let offset=0,failed=0;const mode=$(\'mode\').value;const limit=Number($(\'limit\').value);let sym=\'\';if(single){sym=$(\'symbol\').value.trim().toUpperCase().replace(/[\\s\\/-]/g,\'\');if(!/^[A-Z0-9]{2,25}(USDT)?$/.test(sym)){busy(false);$(\'status\').textContent=\'코인 이름은 영문·숫자로 입력하세요. 예: XRP 또는 XRPUSDT\';return}if(!sym.endsWith(\'USDT\'))sym+=\'USDT\';if(sym===\'USDT\'){busy(false);$(\'status\').textContent=\'검색할 코인 이름을 입력하세요.\';return}}let target=single?1:limit;try{while(!cancel){$(\'status\').textContent=`${single?sym+\' 개별 분석\':\'자동 스캔\'} 중… ${offset}종목 확인 · 성공 ${items.length}건 · 실패 ${failed}건`;const url=`/api/v13-scan?mode=${encodeURIComponent(mode)}&offset=${offset}${single?\'&symbol=\'+encodeURIComponent(sym):\'\'}`;let j;try{j=await request(url)}catch(err){if(cancel)break;failed++;if(single)throw err;offset++;$(\'status\').textContent=`${offset}번째 종목 요청 실패 · 다음 종목으로 진행합니다. (${err.message})`;if(failed>=5&&items.length===0)throw Error(\'연속 오류가 발생했습니다. 잠시 후 다시 시도하세요.\');}if(j){items.push(...(j.results||[]));failed+=(j.errors||[]).length;const next=Number(j.next_offset);if(!Number.isFinite(next)||next<=offset)throw Error(\'서버가 다음 분석 위치를 반환하지 않았습니다.\');offset=next;if(!single){target=limit?Math.min(limit,Number(j.total)||limit):Number(j.total)||offset;}if(single&&j.errors?.length)throw Error(j.errors.map(z=>z.error||\'상장 여부 또는 캔들 조회 실패\').join(\' / \'));}render();$(\'bar\').style.width=`${Math.min(100,Math.round(offset/Math.max(1,target)*100))}%`;if(single||offset>=target)break;}$(\'status\').textContent=cancel?`분석 중지 · 성공 ${items.length}건 · 실패 ${failed}건`:`분석 완료 · 성공 ${items.length}건 · 실패 ${failed}건 (${new Date().toLocaleTimeString(\'ko-KR\')})`;}catch(err){$(\'status\').textContent=`분석 오류: ${err.message} · 성공 ${items.length}건 · 실패 ${failed}건`;}finally{busy(false);controller=null}}\n$(\'scan\').addEventListener(\'click\',()=>start(false));$(\'single\').addEventListener(\'click\',()=>start(true));$(\'symbol\').addEventListener(\'keydown\',ev=>{if(ev.key===\'Enter\'){ev.preventDefault();start(true)}});$(\'stop\').addEventListener(\'click\',()=>{cancel=true;controller?.abort();$(\'status\').textContent=\'중지 요청 중…\'});$(\'filter\').addEventListener(\'change\',render);\n\n\n</script></body></html>\n'

"""BADANG 1.8: on-demand OKX OI history, timestamp-window trade CVD and trade VWAP.

Never mark a truncated trade sample as full-window CVD or exact full-window VWAP.
No automated orders, no fabricated history, no persistent database requirement.
"""
import time
from badang_derivatives_v15 import fetch, number, okx_symbol, vwap_from_candles

WINDOW_MS = 15 * 60 * 1000
MAX_TRADE_PAGES = 8  # 800 trades/request; bound latency for Render; incomplete windows clearly marked

def oi_history(inst, now_ms, session=None):
    """Compare historical OI in contracts at 15m/1h; no interpolation across large gaps."""
    try:
        rows = fetch('/api/v5/rubik/stat/contracts/open-interest-history',
                     {'instId': inst, 'period': '5m', 'limit': '30'}, session)
        samples = []
        for r in rows:
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                ts, oi = int(r[0]), number(r[1])
            elif isinstance(r, dict):
                ts, oi = int(r.get('ts')), number(r.get('oi'))
            else:
                continue
            if oi is not None and oi > 0 and 0 <= now_ms - ts <= 2 * 3600000:
                samples.append((ts, oi))
        samples.sort()
        if not samples or now_ms - samples[-1][0] > 10 * 60000:
            return {'status': 'UNAVAILABLE', 'reason': 'STALE_OR_EMPTY_HISTORY'}
        latest_ts, latest = samples[-1]
        output = {'status': 'OK', 'source': 'OKX_5M_HISTORY', 'latest_oi': latest,
                  'latest_ts_ms': latest_ts, 'change_15m_pct': None, 'change_1h_pct': None}
        for mins, key in [(15, 'change_15m_pct'), (60, 'change_1h_pct')]:
            target = latest_ts - mins * 60000
            nearby = min(samples, key=lambda x: abs(x[0] - target))
            if abs(nearby[0] - target) <= 5 * 60000 and nearby[1] > 0:
                output[key] = round((latest / nearby[1] - 1) * 100, 4)
        if output['change_15m_pct'] is None and output['change_1h_pct'] is None:
            output['status'] = 'INSUFFICIENT_HISTORY'
        return output
    except Exception as exc:
        return {'status': 'UNAVAILABLE', 'reason': type(exc).__name__}

def trade_window(inst, now_ms, session=None, pages=None):
    """Bounded OKX history traversal; coverage means timestamp reach, not full exchange feed."""
    import os
    cutoff = now_ms - WINDOW_MS
    try:
        limit_pages = min(120, max(3, int(os.environ.get('BADANG_TRADE_PAGES', '24')))) if pages is None else pages
    except (ValueError, TypeError):
        limit_pages = 24
    seen, records, cursor, reached, errors = set(), [], None, False, []
    last_oldest = None
    for page in range(limit_pages):
        params = {'instId':inst, 'limit':'100', 'type':'1'}
        if cursor is not None: params['after'] = cursor
        try: batch = fetch('/api/v5/market/history-trades',params,session)
        except Exception as exc:
            errors.append(type(exc).__name__);break
        if not batch: break
        ids=[]
        for row in batch:
            try:
                tid=str(row['tradeId']);ts=int(row['ts']);px=number(row.get('px'));sz=number(row.get('sz'));side=row.get('side')
            except (KeyError,ValueError,TypeError,OverflowError): continue
            if not tid.isdigit():continue
            ids.append(int(tid))
            if ts<cutoff:reached=True;continue
            if ts>now_ms+60000 or tid in seen or px is None or px<=0 or sz is None or sz<=0 or side not in ('buy','sell'):continue
            seen.add(tid);records.append((ts,px,sz,side))
        if not ids:break
        nxt=min(ids)
        if cursor is not None and nxt>=int(cursor):errors.append('PAGINATION_STALLED');break
        cursor=str(nxt)
        if reached:break
        if len(batch)<100:break
    records.sort()
    buy=sum(sz for _,_,sz,side in records if side=='buy')
    sell=sum(sz for _,_,sz,side in records if side=='sell')
    vol=buy+sell
    vwap=sum(px*sz for _,px,sz,_ in records)/vol if vol else None
    timestamp_reached=bool(reached and not errors)
    return {'status':'TIMESTAMP_REACHED_UNVERIFIED' if timestamp_reached else 'PARTIAL_WINDOW',
      'window_minutes':15,'coverage_confirmed':False,'timestamp_boundary_reached':timestamp_reached,
      'exchange_wide_completeness_verified':False,'count':len(records),'pages_requested':page+1,
      'oldest_ts_ms':records[0][0] if records else None,'newest_ts_ms':records[-1][0] if records else None,
      'cvd_contracts':round(buy-sell,8) if vol else None,'buy_contracts':round(buy,8),
      'sell_contracts':round(sell,8),'imbalance':round((buy-sell)/vol,6) if vol else None,
      'vwap':round(vwap,10) if vwap is not None else None,
      'vwap_exact_for_retrieved_trades':bool(vol),'full_market_completeness_guaranteed':False,
      'errors':errors}


# BADANG 2.0: durable rolling trade observer, BTC/ETH first.
# Polling cannot prove exchange-wide completeness; strict quality gate remains.
import sqlite3
from collections import deque

BADANG_DB = os.environ.get('BADANG_DB_PATH', '/tmp/badang_trades_v20.sqlite3')
BADANG_POLL_SECONDS = max(1.0, float(os.environ.get('BADANG_POLL_SECONDS','2.0')))
BADANG_COLLECTOR = {'started':False,'last_error':None,'last_success':{},'last_poll':{},'gap_count':{},'lock':threading.RLock()}
BADANG_SYMBOLS = ('BTC-USDT-SWAP','ETH-USDT-SWAP')

def badang_db():
    db=sqlite3.connect(BADANG_DB, timeout=10)
    db.execute('PRAGMA busy_timeout=10000')
    db.execute('CREATE TABLE IF NOT EXISTS trades (inst TEXT NOT NULL, trade_id TEXT NOT NULL, ts INTEGER NOT NULL, px REAL NOT NULL, sz REAL NOT NULL, side TEXT NOT NULL, PRIMARY KEY(inst,trade_id))')
    db.execute('CREATE INDEX IF NOT EXISTS trades_inst_ts ON trades(inst,ts)')
    db.execute('CREATE TABLE IF NOT EXISTS intervals (inst TEXT NOT NULL, ts INTEGER NOT NULL, ok INTEGER NOT NULL, reason TEXT, PRIMARY KEY(inst,ts))')
    db.commit()
    return db

def badang_poll_once(inst):
    # Latest trades from exchange; every cycle must complete before the next.
    # API limit 100; if throughput exceeds polling capacity, explicitly mark a gap.
    from badang_derivatives_v15 import fetch
    now=int(time.time()*1000)
    try:
        batch=fetch('/api/v5/market/trades', {'instId':inst,'limit':'100'})
        valid=[]
        for x in batch:
            try:
                tid=str(x['tradeId']);ts=int(x['ts']);px=float(x['px']);sz=float(x['sz']);side=x['side']
                if tid.isdigit() and 0<px and 0<sz and side in ('buy','sell') and ts<=now+60000:
                    valid.append((inst,tid,ts,px,sz,side))
            except (ValueError,TypeError,KeyError):continue
        if not valid: raise ValueError('EMPTY_TRADE_RESPONSE')
        oldest=min(r[2] for r in valid)
        with BADANG_COLLECTOR['lock']:
            previous=BADANG_COLLECTOR['last_poll'].get(inst)
            BADANG_COLLECTOR['last_poll'][inst]=now
            BADANG_COLLECTOR['last_success'][inst]=now
            # A 100-trade cap and nonoverlapping time windows are data-quality warnings.
            suspect=bool(previous is not None and oldest>previous+2000)
            if suspect: BADANG_COLLECTOR['gap_count'][inst]=BADANG_COLLECTOR['gap_count'].get(inst,0)+1
        with badang_db() as db:
            db.executemany('INSERT OR IGNORE INTO trades VALUES (?,?,?,?,?,?)',valid)
            db.execute('INSERT OR REPLACE INTO intervals VALUES (?,?,?,?)',(inst,now,0 if suspect else 1,'POSSIBLE_MISSED_TRADES' if suspect else 'OBSERVED'))
            db.execute('DELETE FROM trades WHERE ts < ?', (now-2*3600*1000,))
            db.execute('DELETE FROM intervals WHERE ts < ?', (now-2*3600*1000,))
        return len(valid)
    except Exception as exc:
        with BADANG_COLLECTOR['lock']:
            BADANG_COLLECTOR['last_error']=f'{inst}: {type(exc).__name__}'
            BADANG_COLLECTOR['last_poll'][inst]=now
            BADANG_COLLECTOR['gap_count'][inst]=BADANG_COLLECTOR['gap_count'].get(inst,0)+1
        try:
            with badang_db() as db:db.execute('INSERT OR REPLACE INTO intervals VALUES (?,?,?,?)',(inst,now,0,type(exc).__name__))
        except Exception:pass
        return 0

def badang_observed_window(inst):
    now=int(time.time()*1000);cutoff=now-15*60000
    with badang_db() as db:
        rows=db.execute('SELECT ts,px,sz,side FROM trades WHERE inst=? AND ts>=? AND ts<=?',(inst,cutoff,now)).fetchall()
        intervals=db.execute('SELECT ts,ok FROM intervals WHERE inst=? AND ts>=? ORDER BY ts',(inst,cutoff)).fetchall()
    buy=sum(r[2] for r in rows if r[3]=='buy');sell=sum(r[2] for r in rows if r[3]=='sell');vol=buy+sell
    first=min((r[0] for r in rows),default=None);last=max((r[0] for r in rows),default=None)
    # Strictly disallow certified full market feed: REST polling cannot prove every trade.
    continuous=bool(intervals and intervals[0][0]-cutoff<=15000 and now-intervals[-1][0]<=15000 and all(r[1] for r in intervals) and all(b[0]-a[0]<=15000 for a,b in zip(intervals,intervals[1:])))
    return {'source':'OKX_PUBLIC_TRADES_CONTINUOUS_POLL','count':len(rows),'window_minutes':15,
      'oldest_ts_ms':first,'newest_ts_ms':last,'observed_seconds':round((last-first)/1000,1) if first and last else 0,
      'buy_contracts':round(buy,8),'sell_contracts':round(sell,8),'cvd_contracts':round(buy-sell,8) if vol else None,
      'imbalance':round((buy-sell)/vol,6) if vol else None,
      'vwap':round(sum(r[1]*r[2] for r in rows)/vol,10) if vol else None,
      'poll_continuity':continuous,'coverage_confirmed':False,
      'full_market_completeness_guaranteed':False,
      'status':'CONTINUOUS_POLL_UNVERIFIED' if continuous else 'WARMING_OR_GAPS',
      'intervals':len(intervals),'gaps':sum(1 for r in intervals if not r[1])}

def badang_collector_loop():
    while True:
        for inst in BADANG_SYMBOLS:badang_poll_once(inst)
        time.sleep(BADANG_POLL_SECONDS)

def badang_start_collector():
    if os.environ.get('BADANG_DISABLE_COLLECTOR')=='1':return
    # A local lock prevents duplicate pollers across gunicorn workers on one machine.
    try:
        import fcntl
        lockfile=open('/tmp/badang_collector_v20.lock','w')
        fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
        BADANG_COLLECTOR['lockfile']=lockfile
    except (ImportError,OSError):return
    BADANG_COLLECTOR['started']=True
    threading.Thread(target=badang_collector_loop,name='badang-collector',daemon=True).start()

@app.route('/api/badang-collector')
def badang_collector_status():
    output={}
    for inst in BADANG_SYMBOLS:
        try:output[inst]=badang_observed_window(inst)
        except Exception as exc:output[inst]={'status':'ERROR','reason':type(exc).__name__}
    return jsonify(version='2.0.0',collector_running=BADANG_COLLECTOR['started'],
                   last_success=BADANG_COLLECTOR['last_success'],last_error=BADANG_COLLECTOR['last_error'],
                   instruments=output,note='REST polling cannot certify exchange-wide completeness; read-only research.')

badang_start_collector()

def research_v18(item, candles, session=None):
    """Integrate the new indicators without misrepresenting partial data as certainty."""
    inst = okx_symbol(item.get('symbol', ''))
    now = int(time.time() * 1000)
    result = {'version': '2.0.0', 'status': 'RESEARCH_ONLY', 'eligible_for_alert': False,
              'source_exchange': 'okx', 'instrument': inst, 'observed_at_ms': now,
              'collection': 'CONTINUOUS_REST_POLL_BTC_ETH' if inst in BADANG_SYMBOLS else 'ON_DEMAND', 'database_required': True,
              'vwap': vwap_from_candles(candles), 'complete_hour_cvd': False,
              'oi_change_15m_pct': None, 'oi_change_1h_pct': None,
              'oi_change_status': 'UNAVAILABLE', 'checks': {}, 'errors': {},
              'reason': '실제 거래 자료의 수집 범위를 표시하며 자동 진입 신호가 아님'}
    if not inst:
        result['data_status'] = 'UNSUPPORTED_SYMBOL';return result
    try:
        rows = fetch('/api/v5/public/open-interest', {'instType':'SWAP','instId':inst},session)
        r = next((r for r in rows if r.get('instId') == inst), None)
        ts = int(r['ts']) if r and r.get('ts') else 0
        result['oi_contracts'] = number(r.get('oi')) if r and abs(now-ts)<180000 else None
        result['oi_exchange_ts_ms'] = ts or None
    except Exception as exc:
        result['errors']['oi'] = type(exc).__name__;result['oi_contracts'] = None
    try:
        rows = fetch('/api/v5/public/funding-rate', {'instId':inst},session)
        r = next((r for r in rows if r.get('instId') == inst), None)
        result['funding_rate'] = number(r.get('fundingRate')) if r else None
    except Exception as exc:
        result['errors']['funding'] = type(exc).__name__;result['funding_rate'] = None
    history = oi_history(inst,now,session)
    result['oi_history'] = history
    result['oi_change_status'] = history['status']
    result['oi_change_15m_pct'] = history.get('change_15m_pct')
    result['oi_change_1h_pct'] = history.get('change_1h_pct')
    trades = badang_observed_window(inst) if inst in BADANG_SYMBOLS else trade_window(inst,now,session,pages=4)
    result['trade_window'] = trades
    result['trade_sample_count'] = trades['count']
    result['sample_delta_contracts'] = trades['cvd_contracts']
    result['sample_imbalance'] = trades['imbalance']
    result['sample_span_seconds'] = ((trades['newest_ts_ms']-trades['oldest_ts_ms'])/1000
                                     if trades['oldest_ts_ms'] is not None else None)
    result['cvd_15m_contracts'] = trades['cvd_contracts'] if trades['coverage_confirmed'] else None
    result['trade_vwap_15m'] = trades['vwap'] if trades['coverage_confirmed'] else None
    result['trade_vwap_status'] = trades['status']
    side = item.get('recommendation')
    imbalance = trades['imbalance']
    result['checks'] = {
        'trend_aligned': item.get('trend_aligned') is True,
        'oi_history_available': history.get('change_15m_pct') is not None,
        'recent_trade_sample_agrees': side in ('LONG','SHORT') and imbalance is not None and trades['count']>=40 and
              (imbalance >= .12 if side=='LONG' else imbalance <= -.12),
        'trade_window_complete': trades['coverage_confirmed'],
        'vwap_confirmed': side in ('LONG','SHORT') and trades['coverage_confirmed'] and trades['vwap'] is not None and
              item.get('entry_reference') is not None and
              (float(item['entry_reference']) > trades['vwap'] if side=='LONG' else float(item['entry_reference']) < trades['vwap'])
    }
    result['data_status'] = 'OI_OK_TRADES_UNVERIFIED' if history['status']=='OK' else 'PARTIAL'
    return result



@app.route('/api/badang-version')
def badang_version():
    return jsonify(version='2.0.4', mode='READ_ONLY',
        trades='BTC/ETH: continuously polled public trades in SQLite, completeness unverified',
        cvd='OBSERVED_15M_UNCERTIFIED', vwap='OBSERVED_TRADES_AND_CANDLE_APPROX',
        signals='TECHNICAL_CANDIDATES_WITH_DATA_CAVEATS',
        note='A complete historical tick feed cannot be guaranteed by bounded public REST calls.')

@app.route('/api/badang-health')
def badang_health():
    """Live OKX API diagnostics. This is NOT a trading recommendation."""
    from badang_derivatives_v15 import fetch
    checks = {}
    for name, path, params in [
        ('server_time','/api/v5/public/time',{}),
        ('btc_oi','/api/v5/public/open-interest',{'instType':'SWAP','instId':'BTC-USDT-SWAP'}),
        ('btc_funding','/api/v5/public/funding-rate',{'instId':'BTC-USDT-SWAP'}),
        ('btc_trades','/api/v5/market/history-trades',{'instId':'BTC-USDT-SWAP','limit':'1'}),
        ('btc_oi_history','/api/v5/rubik/stat/contracts/open-interest-history',{'instId':'BTC-USDT-SWAP','period':'5m','limit':'2'}),
        ('eth_oi','/api/v5/public/open-interest',{'instType':'SWAP','instId':'ETH-USDT-SWAP'}),
        ('eth_funding','/api/v5/public/funding-rate',{'instId':'ETH-USDT-SWAP'}),
        ('eth_trades','/api/v5/market/history-trades',{'instId':'ETH-USDT-SWAP','limit':'1'})
    ]:
        try:
            rows=fetch(path,params)
            checks[name]={'status':'OK' if rows else 'EMPTY','count':len(rows)}
        except Exception as exc:
            checks[name]={'status':'ERROR','error_type':type(exc).__name__}
    return jsonify(version='2.0.1', live_test=True,
                   all_ok=all(v['status']=='OK' for v in checks.values()), checks=checks,
                   note='Data API diagnostics only. Complete 15m CVD is not guaranteed.')


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
