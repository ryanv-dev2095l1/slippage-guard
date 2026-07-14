import time
from decimal import Decimal
import httpx
from slippage_guard.types import OrderBook, Exchange


TIMEOUT = 6.0
MAX_RETRIES = 2


def _request_with_retry(url: str, params: dict = None, headers: dict = None) -> dict:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429:
                # rate limited, back off briefly
                time.sleep(0.4 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(f"failed fetching {url} after {MAX_RETRIES + 1} attempts: {last_err}")


def _sort_book(bids, asks):
    # make sure bids are descending and asks are ascending regardless of upstream quirks
    sorted_bids = sorted(bids, key=lambda x: x[0], reverse=True)
    sorted_asks = sorted(asks, key=lambda x: x[0], reverse=False)
    return sorted_bids, sorted_asks


def fetch_binance(symbol: str, limit: int = 100) -> OrderBook:
    url = "https://api.binance.com/api/v3/depth"
    clean_sym = symbol.replace("-", "").replace("/", "").replace("_", "").upper()
    data = _request_with_retry(url, params={"symbol": clean_sym, "limit": limit})

    bids = [(Decimal(p), Decimal(s)) for p, s in data.get("bids", [])]
    asks = [(Decimal(p), Decimal(s)) for p, s in data.get("asks", [])]
    bids, asks = _sort_book(bids, asks)
    return OrderBook(exchange=Exchange.BINANCE, symbol=symbol, bids=bids, asks=asks)


def fetch_coinbase(symbol: str) -> OrderBook:
    clean_sym = symbol.replace("/", "-").replace("_", "-").upper()
    url = f"https://api.exchange.coinbase.com/products/{clean_sym}/book?level=2"
    # coinbase requires user-agent now or returns 403 on some cloud IPs
    headers = {"User-Agent": "slippage-guard/0.1"}
    data = _request_with_retry(url, headers=headers)

    bids = [(Decimal(item[0]), Decimal(item[1])) for item in data.get("bids", [])]
    asks = [(Decimal(item[0]), Decimal(item[1])) for item in data.get("asks", [])]
    bids, asks = _sort_book(bids, asks)
    return OrderBook(exchange=Exchange.COINBASE, symbol=symbol, bids=bids, asks=asks)


def fetch_kraken(symbol: str, count: int = 100) -> OrderBook:
    # FIXME: add a proper pair normalizer table instead of this ad-hoc if/else
    clean_sym = symbol.replace("/", "").replace("-", "").replace("_", "").upper()
    if clean_sym == "BTCUSD":
        clean_sym = "XXBTZUSD"
    elif clean_sym == "ETHUSD":
        clean_sym = "XETHZUSD"
    elif clean_sym == "BTCUSDT":
        clean_sym = "XBTUSDT"

    url = "https://api.kraken.com/0/public/Depth"
    data = _request_with_retry(url, params={"pair": clean_sym, "count": count})
    if data.get("error"):
        raise RuntimeError(f"kraken error: {data['error']}")

    result = data["result"]
    pair_key = next(iter(result))
    pair_data = result[pair_key]

    bids = [(Decimal(item[0]), Decimal(item[1])) for item in pair_data.get("bids", [])]
    asks = [(Decimal(item[0]), Decimal(item[1])) for item in pair_data.get("asks", [])]
    bids, asks = _sort_book(bids, asks)
    return OrderBook(exchange=Exchange.KRAKEN, symbol=symbol, bids=bids, asks=asks)


def get_order_book(exchange: Exchange, symbol: str, depth: int = 100) -> OrderBook:
    if exchange == Exchange.BINANCE:
        return fetch_binance(symbol, depth)
    elif exchange == Exchange.COINBASE:
        return fetch_coinbase(symbol)
    elif exchange == Exchange.KRAKEN:
        return fetch_kraken(symbol, depth)
    raise ValueError(f"unsupported exchange: {exchange}")
