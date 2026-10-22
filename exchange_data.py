import requests

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

        # OKX volCcy24h is base-currency volume for these swaps.
        volume = float(item.get("volCcy24h") or 0)
        price = float(item.get("last") or 0)
        turnover = volume * price

        if turnover >= min_turnover:
            result.append((symbol, turnover))

    return sorted(result, key=lambda x: x[1], reverse=True)

TIMEFRAMES = {
    "5m": "5m",
    "15m": "15m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
}


def binance_candles(symbol, timeframe, limit=230):
    """Return [timestamp, open, high, low, close, base_volume, quote_volume]."""
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
    """Return [timestamp, open, high, low, close, base_volume, quote_volume]."""
    bar = {
        "5m": "5m",
        "15m": "15m",
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
