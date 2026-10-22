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
