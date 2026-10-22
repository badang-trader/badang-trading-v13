import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

SESSION = requests.Session()
TIMEOUT = 15


def get_json(url, params=None):
    response = SESSION.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def binance_symbols(min_turnover=1000000):
    """Binance USDT perpetual futures symbols."""
    base = "https://fapi.binance.com"
    info = get_json(base + "/fapi/v1/exchangeInfo")
    tickers = get_json(base + "/fapi/v1/ticker/24hr")

    allowed = {
        item["symbol"]
        for item in info.get("symbols", [])
        if item.get("quoteAsset") == "USDT"
        and item.get("contractType") == "PERPETUAL"
        and item.get("status") == "TRADING"
    }

    result = []
    for item in tickers:
        symbol = item.get("symbol", "")
        turnover = float(item.get("quoteVolume", 0))
        if symbol in allowed and turnover >= min_turnover:
            result.append((symbol, turnover))

    return sorted(result, key=lambda x: x[1], reverse=True)


def okx_symbols(min_turnover=1000000):
    """OKX USDT perpetual swap symbols."""
    base = "https://www.okx.com"
    instruments = get_json(
        base + "/api/v5/public/instruments",
        {"instType": "SWAP"}
    )
    tickers = get_json(
        base + "/api/v5/market/tickers",
        {"instType": "SWAP"}
    )

    allowed = {
        item["instId"]
        for item in instruments.get("data", [])
        if item.get("settleCcy") == "USDT"
        and item.get("state") == "live"
        and item.get("ctType") == "linear"
    }

    result = []
    for item in tickers.get("data", []):
        symbol = item.get("instId", "")
        if symbol not in allowed:
            continue

        volume = float(item.get("volCcy24h") or 0)
        price = float(item.get("last") or 0)
        turnover = volume * price

        if turnover >= min_turnover:
            result.append((symbol, turnover))

    return sorted(result, key=lambda x: x[1], reverse=True)


TIMEFRAMES = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
}


def binance_candles(symbol, timeframe, limit=230):
    """Return timestamp, OHLC, base volume and quote volume."""
    interval = TIMEFRAMES[timeframe]
    data = get_json(
        "https://fapi.binance.com/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )
    return [
        [
            int(row[0]),
            float(row[1]),
            float(row[2]),
            float(row[3]),
            float(row[4]),
            float(row[5]),
            float(row[7]),
        ]
        for row in data
    ]


def okx_candles(symbol, timeframe, limit=230):
    """Fetch completed OKX candles."""
    bar = {
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1H": "1H",
        "4H": "4H",
        "1D": "1D",
    }[timeframe]

    collected = {}
    after = None

    while len(collected) < limit:
        params = {
            "instId": symbol,
            "bar": bar,
            "limit": min(100, limit - len(collected)),
        }
        if after is not None:
            params["after"] = after

        result = get_json(
            "https://www.okx.com/api/v5/market/history-candles",
            params,
        )
        if result.get("code") != "0":
            raise ValueError(result.get("msg", "OKX candle error"))

        rows = result.get("data", [])
        if not rows:
            break

        for row in rows:
            if row[8] == "1":
                collected[int(row[0])] = [
                    int(row[0]),
                    float(row[1]),
                    float(row[2]),
                    float(row[3]),
                    float(row[4]),
                    float(row[5]),
                    float(row[7]),
                ]

        oldest = min(int(row[0]) for row in rows)
        if after is not None and oldest >= int(after):
            break
        after = str(oldest)

    return [collected[t] for t in sorted(collected)][-limit:]


def fastest_candles(symbol, timeframe, limit=230, exchanges=None):
    """Fetch candles concurrently and use the first valid response."""
    if exchanges is None:
        exchanges = ("bitget", "binance", "okx")

    providers = {
        "bitget": bitget_candles,
        "binance": binance_candles,
        "okx": okx_candles,
    }

    def fetch_one(exchange):
        if exchange not in providers:
            raise ValueError("Unsupported provider: " + exchange)

        if exchange == "okx":
            exchange_symbol = symbol.replace("USDT", "-USDT-SWAP")
        else:
            exchange_symbol = symbol

        started = time.monotonic()
        rows = providers[exchange](exchange_symbol, timeframe, limit)
        rows = validate_candles(rows, timeframe)
        if len(rows) < 205:
            raise ValueError("Insufficient candles")

        return {
            "exchange": exchange,
            "symbol": exchange_symbol,
            "timeframe": timeframe,
            "candles": rows,
            "latency_ms": round(
                (time.monotonic() - started) * 1000
            ),
        }

    selected = [name for name in exchanges if name in providers]
    if not selected:
        raise ValueError("No available candle providers")

    errors = {}
    pool = ThreadPoolExecutor(max_workers=len(selected))
    futures = {
        pool.submit(fetch_one, name): name
        for name in selected
    }

    try:
        for future in as_completed(futures):
            name = futures[future]
            try:
                return future.result()
            except Exception as exc:
                errors[name] = str(exc)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    raise ValueError("All exchanges failed: " + str(errors))


def validate_candles(rows, timeframe, minimum=205):
    """Keep only completed candles and validate OHLCV data."""
    minutes = {
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1H": 60,
        "4H": 240,
        "1D": 1440,
    }
    interval_ms = minutes[timeframe] * 60000
    now_ms = int(time.time() * 1000)
    valid = {}

    for row in rows:
        try:
            ts = int(row[0])
            op, hi, lo, cl = map(float, row[1:5])
            volume = float(row[5])

            if ts + interval_ms > now_ms:
                continue
            if min(op, hi, lo, cl) <= 0 or volume < 0:
                continue
            if hi < max(op, cl) or lo > min(op, cl):
                continue

            valid[ts] = row
        except (ValueError, TypeError, IndexError):
            continue

    result = [valid[t] for t in sorted(valid)]

    if len(result) < minimum:
        raise ValueError(
            f"Completed candles insufficient: "
            f"{len(result)}/{minimum}"
        )

    return result


def bitget_candles(symbol, timeframe, limit=230):
    """Fetch completed Bitget USDT futures candles."""
    interval_ms = {
        "5m": 300000,
        "15m": 900000,
        "30m": 1800000,
        "1H": 3600000,
        "4H": 14400000,
        "1D": 86400000,
    }[timeframe]

    now_ms = int(time.time() * 1000)
    end_time = (now_ms // interval_ms) * interval_ms - 1
    collected = {}

    for _ in range(5):
        result = get_json(
            "https://api.bitget.com/api/v2/mix/market/history-candles",
            {
                "symbol": symbol,
                "productType": "USDT-FUTURES",
                "granularity": timeframe,
                "endTime": str(end_time),
                "limit": "100",
            },
        )

        if result.get("code") != "00000":
            raise ValueError(
                result.get("msg", "Bitget API error"
            ))

        rows = result.get("data") or []
        if not rows:
            break

        for row in rows:
            ts = int(row[0])
            if ts + interval_ms <= now_ms:
                collected[ts] = [
                    ts,
                    float(row[1]),
                    float(row[2]),
                    float(row[3]),
                    float(row[4]),
                    float(row[5]),
                    float(row[6]),
                ]

        if len(collected) >= limit:
            break

        oldest = min(int(row[0]) for row in rows)
        if oldest >= end_time:
            break
        end_time = oldest - 1

    return [
        collected[t] for t in sorted(collected)
    ][-limit:]

