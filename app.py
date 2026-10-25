import os
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


@app.route('/api/v13-scan')
def v13_scan():
    from exchange_data import fastest_candles
    from badang_analysis_v13 import (
        analyze,
        top_five,
        ema
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

        universe = [
            'BTCUSDT',
            'ETHUSDT'
        ] + [
            s for s, _ in symbols(1000000)
            if s not in (
                'BTCUSDT', 'ETHUSDT'
            )
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

                item['timeframe_trends'] = trends

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
                item['exchange'] = data['exchange']
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
                side = item.get('candidate_side')
                score = item.get('long_score', 0) if side == 'LONG' else item.get('short_score', 0)
                rr = finite_number(item.get('risk_reward_1'))
                plan_ok = ('INVALID_TRADE_PLAN' not in item.get('stability_warnings', [])
                           and rr is not None and rr >= 1.5)
                # Only valid, aligned plans may be promoted. Missing flow never automatically blocks.
                eligible = (item.get('status') == 'ok' and side in ('LONG', 'SHORT')
                            and score >= 80 and item.get('trend_aligned') and plan_ok)
                item['recommendation'] = side if eligible else 'WAIT'
                item['signal_grade'] = ('STRONG_CANDIDATE' if score >= 90 else 'GOOD_CANDIDATE') if eligible else ('WATCHLIST' if score >= 70 else 'WAIT')
                item['entry_blockers'] = []
                if not item.get('trend_aligned'):
                    item['entry_blockers'].append('TIMEFRAMES_NOT_ALIGNED')
                if score < 80:
                    item['entry_blockers'].append('TECHNICAL_SCORE_BELOW_80')
                if not plan_ok:
                    item['entry_blockers'].append('INVALID_PLAN_OR_RISK_REWARD_BELOW_1_5')
                item['signal_type'] = 'TECHNICAL_CANDIDATE_NOT_EXECUTION_ORDER'
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


BADANG_ORIGINAL_HTML = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0c1424"><title>BADANG Trading · 원래 화면</title><style>:root{font-family:system-ui,-apple-system,\'Noto Sans KR\',sans-serif;color:#edf3fb;background:#0c1424}*{box-sizing:border-box}body{margin:0}main{max-width:720px;margin:auto;padding:18px 14px 42px}header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:20px}.brand{font-size:19px;font-weight:800;white-space:nowrap}.brand span{font-weight:400;color:#9ab1d3}small{font-size:11px;color:#9baec9}h1{font-size:25px;margin:0 0 8px}h2{font-size:18px;margin:0}.hero,.item{background:#16243a;border:1px solid #2a3b54;border-radius:18px;padding:18px;margin-bottom:13px}.hero p{color:#9db0c8;font-size:13px;line-height:1.6}.controls{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:20px 0}label{font-size:12px;color:#a6b8d0}select{display:block;width:100%;background:#0c192c;color:#f2f6fc;border:1px solid #364b67;border-radius:10px;padding:11px 8px;margin-top:6px;font-size:13px}button{border:0;border-radius:12px;padding:15px;background:#40bcae;color:#071a23;font-size:15px;font-weight:800;width:100%;cursor:pointer}button:disabled{opacity:.5;cursor:wait}.status{min-height:20px}.progress{height:5px;background:#293a52;border-radius:8px;overflow:hidden}.progress>div{height:100%;width:0;background:#40bcae;transition:width .3s}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:15px 0 26px}.summary>div{padding:14px 10px;background:#152237;border-radius:12px}.summary span{display:block;color:#9eb0c9;font-size:11px}.summary strong{display:block;font-size:19px;margin-top:6px}.heading{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px}.heading select{width:115px;margin:0}.top{display:flex;justify-content:space-between;gap:10px;align-items:start}.top strong{font-size:17px}.top small{display:block;margin-top:5px}.signal{font-size:12px;font-weight:800;border-radius:8px;padding:8px;white-space:nowrap}.long{color:#63d9bc;background:#124b43}.short{color:#ff9b9b;background:#572d3b}.wait{color:#c4cbd4;background:#344156}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:18px 0}.metrics div{font-size:11px;color:#9eafc8}.metrics strong{display:block;font-size:15px;color:#eaf1fa;margin-top:5px}details{border-top:1px solid #34455d;padding-top:10px;font-size:12px;color:#c3d2e6}summary{cursor:pointer}details p{line-height:1.7}.empty{padding:32px 10px;text-align:center;color:#9cacc1;border:1px dashed #42536b;border-radius:14px}footer{font-size:11px;color:#90a4be;line-height:1.7;margin-top:25px}@media(max-width:390px){header{display:block}header small{display:block;margin-top:5px}.controls{grid-template-columns:1fr}}\n</style></head><body><main><header><div class="brand">🌊 BADANG <span>Trading</span></div><small>BADANG 2.0 BTC·ETH 연속 관측 엔진 · 공개 데이터</small></header><section class="hero"><h1>롱·숏 신호 스캐너</h1><p>기존 화면 구성 그대로 · 최신 분석 엔진으로 종목을 분석합니다.</p><div class="controls"><label>분석 모드<select id="interval"><option value="scalp">단타 · 15분 / 30분 / 1시간</option><option value="swing">스윙 · 1시간 / 4시간 / 일봉</option></select></label><label>분석 범위<select id="minVolume"><option value="5">상위 5종목</option><option value="20" selected>상위 20종목</option><option value="50">상위 50종목</option><option value="0">전체 종목 (시간 소요)</option></select></label></div><button id="scan">종목 스캔 시작 →</button><p class="status" id="status">아직 분석하지 않았습니다.</p><div class="progress"><div id="bar"></div></div></section><section class="summary"><div><span>분석 완료</span><strong id="count">—</strong></div><div><span>롱 후보</span><strong id="longCount">—</strong></div><div><span>숏 후보</span><strong id="shortCount">—</strong></div></section><section><div class="heading"><h2>신호 후보</h2><select id="filter"><option value="ALL">전체</option><option value="LONG">롱만</option><option value="SHORT">숏만</option><option value="WAIT">관망</option></select></div><div id="results" class="results"><div class="empty">스캔 버튼을 눌러 시작하세요.</div></div></section><footer>⚠️ OI·펀딩비·체결 CVD·VWAP 분석은 자료 범위에 따라 제한되며 연구용이며 수익 확률이나 투자 권유가 아닙니다. 시세 지연·API 오류·급변동에 주의하세요. 자동 주문 기능은 없습니다.</footer></main><script>const $=id=>document.getElementById(id);\nlet current=[],running=false,abort=false,allTotal=0;\nconst num=(n,d=4)=>n==null||!Number.isFinite(Number(n))?\'—\':Number(n).toLocaleString(\'ko-KR\',{maximumFractionDigits:d});\nconst esc=s=>String(s??\'\').replace(/[&<>"\']/g,c=>({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',\'"\':\'&quot;\',\'\\\'\':\'&#39;\'}[c]));\nconst reasonMap={\n\'EMA bearish alignment\':\'이동평균선 하락 정렬\',\'EMA bullish alignment\':\'이동평균선 상승 정렬\',\n\'EMA20 below EMA50\':\'EMA20이 EMA50 아래\',\'EMA20 above EMA50\':\'EMA20이 EMA50 위\',\n\'MACD histogram falling negative\':\'MACD 하락세\',\'MACD histogram rising positive\':\'MACD 상승세\',\n\'RSI bearish range\':\'RSI 하락 우세\',\'RSI bullish range\':\'RSI 상승 우세\',\n\'hidden bearish RSI divergence candidate\':\'숨은 하락 다이버전스 후보\',\n\'hidden bullish RSI divergence candidate\':\'숨은 상승 다이버전스 후보\',\n\'rising volume with red candle\':\'음봉 거래량 증가\',\'rising volume with green candle\':\'양봉 거래량 증가\'\n};\nfunction korean(s){return reasonMap[s]||String(s||\'확인 필요\')}\nfunction signal(x){return [\'LONG\',\'SHORT\'].includes(x.recommendation)?x.recommendation:\'WAIT\'}\nfunction render(){\n  const filter=$(\'filter\').value;\n  const data=current.filter(x=>filter===\'ALL\'||signal(x)===filter);\n  data.sort((a,b)=>Math.max(b.long_score||0,b.short_score||0)-Math.max(a.long_score||0,a.short_score||0));\n  $(\'results\').innerHTML=data.length?data.map(x=>{\n    const dir=signal(x), score=dir===\'LONG\'?x.long_score:dir===\'SHORT\'?x.short_score:Math.max(x.long_score||0,x.short_score||0);\n    const v=x.v17_research||{}, tw=v.trade_window||{}, oh=v.oi_history||{}, trends=x.timeframe_trends||{}, price=x.entry_reference;\n    const labels=Object.entries(trends).map(([k,t])=>k+\' \'+(t===\'UP\'?\'상승\':t===\'DOWN\'?\'하락\':\'중립\')).join(\' · \');\n    const warns=(x.stability_warnings||[]).map(w=>w===\'OPPOSING_RECENT_TRADE_SAMPLE\'?\'최근 체결 방향 충돌\':w===\'INVALID_TRADE_PLAN\'?\'가격 시나리오 부적합\':w).join(\' · \');\n    const plan=dir===\'WAIT\'?\'관망 · 진입 신호 없음\':`진입 참고 ${num(price,8)} · 손절 ${num(x.stop_loss,8)} · 1차 목표 ${num(x.take_profit_1,8)} · 2차 목표 ${num(x.take_profit_2,8)}`;\n    return `<article class="item"><div class="top"><div><strong>${esc(x.symbol)}</strong><small>${esc(x.exchange||\'\')} · ${esc(labels)}</small></div><div class="signal ${dir===\'LONG\'?\'long\':dir===\'SHORT\'?\'short\':\'wait\'}">${dir===\'LONG\'?\'롱 후보\':dir===\'SHORT\'?\'숏 후보\':\'관망\'} · ${num(score,0)}점</div></div><div class="metrics"><div>기준 가격<strong>${num(price,8)} USDT</strong></div><div>RSI<strong>${num(x.rsi,2)}</strong></div><div>롱 / 숏 점수<strong>${num(x.long_score,0)} / ${num(x.short_score,0)}</strong></div><div>펀딩비 (OKX)<strong>${num(v.funding_rate==null?null:v.funding_rate*100,4)}%</strong></div></div><details><summary>분석 근거 및 가격 구간</summary><p>${esc((x.reasons||[]).map(korean).join(\' · \')||\'뚜렷한 방향성 신호 없음\')}</p><p><b>최종 판단:</b> ${esc(plan)}</p><p><b>기술적 강도 / 실행 가능성:</b> ${num(x.technical_score,0)}점 (${esc(x.technical_side||\'미확인\')}) · ${esc(x.signal_grade||\'검증 전\')} · 점수는 승률이 아닙니다.</p><p><b>진입 보류 사유:</b> ${esc((x.entry_blockers||[]).join(\' · \')||\'조건 검토 중\')}</p><p><b>다이버전스:</b> ${esc(JSON.stringify(x.divergence_details||x.divergences||[]))}</p><p><b>엘리엇파동 후보 (확정 아님):</b> ${esc(JSON.stringify(x.wave_candidates||[]))}</p><p><b>피보나치:</b> ${esc(JSON.stringify(x.fibonacci||{}))}</p><p><b>데이터 출처:</b> 캔들 ${esc(x.exchange||\'미확인\')} / 파생상품 ${esc(x.derivatives_source_exchange||\'미확인\')} · ${x.derivatives_same_exchange?\'동일 거래소\':\'거래소 혼합 참고값\'}</p><p><b>OI · 펀딩비</b> 현재 OI ${num(v.oi_contracts,2)} 계약 · 15분 변화 ${num(v.oi_change_15m_pct,3)}% · 1시간 변화 ${num(v.oi_change_1h_pct,3)}% · 펀딩 ${num(v.funding_rate==null?null:v.funding_rate*100,4)}%</p><p><b>체결 CVD (15분)</b> ${tw.coverage_confirmed?num(v.cvd_15m_contracts,4)+\' 계약\':\'전체 체결 검증 불가 · 참고용 표본 \'+num(tw.cvd_contracts,4)+\' 계약\'} · 수집 ${num(tw.count,0)}건 · 불균형 ${num(tw.imbalance,3)}</p><p><b>거래 기반 VWAP (15분)</b> ${tw.coverage_confirmed?num(v.trade_vwap_15m,8):\'전체 체결 검증 불가\'} · 수집된 체결 VWAP ${num(tw.vwap,8)}</p><p><b>참고용 캔들 VWAP 근사</b> ${num(v.vwap?.value,8)} · OI 이력 ${esc(oh.status||\'미확인\')}</p>${warns?`<p class="warning">⚠ ${esc(warns)}</p>`:\'\'}<p>점수는 승률이 아니며, 개인 판단용 기술적 후보입니다. 자동 주문 기능은 없습니다.</p></details></article>`;\n  }).join(\'\'):\'<div class="empty">해당 조건의 종목이 없습니다.</div>\';\n}\nasync function begin(){\n if(running)return;\n running=true;abort=false;current=[];allTotal=0;\n $(\'scan\').disabled=true;$(\'bar\').style.width=\'0%\';render();\n const mode=$(\'interval\').value, limit=Number($(\'minVolume\').value);\n let offset=0,errors=0;\n try{\n  while(!abort){\n   $(\'status\').textContent=`분석 중… ${offset}종목 완료`;\n   const res=await fetch(`/api/v13-scan?mode=${encodeURIComponent(mode)}&offset=${offset}`,{cache:\'no-store\'});\n   const j=await res.json();\n   if(!res.ok||j.error)throw Error(j.error||`HTTP ${res.status}`);\n   allTotal=Number(j.total)||0;\n   current.push(...(j.results||[]));errors+=(j.errors||[]).length;\n   const next=Number(j.next_offset);\n   if(!Number.isFinite(next)||next<=offset)throw Error(\'분석 진행 위치 오류\');\n   offset=next;\n   $(\'count\').textContent=current.length+\' / \'+(limit||allTotal);\n   $(\'longCount\').textContent=current.filter(x=>signal(x)===\'LONG\').length;\n   $(\'shortCount\').textContent=current.filter(x=>signal(x)===\'SHORT\').length;\n   const target=limit?Math.min(limit,allTotal):allTotal;\n   $(\'bar\').style.width=(target?Math.min(100,Math.round(offset/target*100)):100)+\'%\';\n   $(\'status\').textContent=`${Math.min(offset,target)} / ${target}종목 확인 · 분석 실패 ${errors}건`;\n   render();\n   if(!j.results?.length&&!j.errors?.length || offset>=target || offset>=allTotal)break;\n  }\n  $(\'status\').textContent+=` · 완료 (${new Date().toLocaleTimeString(\'ko-KR\')})`;\n }catch(e){$(\'status\').textContent=\'오류: \'+e.message}\n finally{running=false;$(\'scan\').disabled=false}\n}\n$(\'scan\').addEventListener(\'click\',begin);\n$(\'filter\').addEventListener(\'change\',render);\n</script></body></html>\n'

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
