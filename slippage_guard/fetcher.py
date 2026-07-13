from decimal import Decimal
import httpx
from slippage_guard.types import OrderBook, Exchange


TIMEOUT_SECONDS = 5.0


def _parse_levels(raw_levels):
    return [(Decimal(p), Decimal(s)) for p, s in raw_levels]


def fetch_binance(symbol: str, limit: int = 100) -> OrderBook:
    url = "https://api.binance.com/api/v3/depth"
    clean_sym = symbol.replace("-", "").replace("/", "").upper()
    resp = httpx.get(url, params={"symbol": clean_sym, "limit": limit}, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    return OrderBook(
        exchange=Exchange.BINANCE,
        symbol=symbol,
        bids=_parse_levels(data["bids"]),
        asks=_parse_levels(data["asks"]),
    )


def fetch_coinbase(symbol: str) -> OrderBook:
    clean_sym = symbol.replace("/", "-").upper()
    url = f"https://api.exchange.coinbase.com/products/{clean_sym}/book?level=2"
    resp = httpx.get(url, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    # coinbase level 2 gives [price, size, num_orders]
    bids = [(Decimal(item[0]), Decimal(item[1])) for item in data["bids"]]
    asks = [(Decimal(item[0]), Decimal(item[1])) for item in data["asks"]]

    return OrderBook(
        exchange=Exchange.COINBASE,
        symbol=symbol,
        bids=bids,
        asks=asks,
    )


def get_order_book(exchange: Exchange, symbol: str, depth: int = 100) -> OrderBook:
    if exchange == Exchange.BINANCE:
        return fetch_binance(symbol, depth)
    elif exchange == Exchange.COINBASE:
        return fetch_coinbase(symbol)
    raise ValueError(f"unsupported exchange: {exchange}")
