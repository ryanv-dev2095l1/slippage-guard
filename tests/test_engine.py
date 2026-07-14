import pytest
from decimal import Decimal
from slippage_guard.types import OrderBook, PriceLevel, OrderSide
from slippage_guard.engine import simulate_execution


def _make_book(bids, asks) -> OrderBook:
    return OrderBook(
        symbol="ETH-USDT",
        exchange="binance",
        bids=[PriceLevel(price=Decimal(str(p)), size=Decimal(str(s))) for p, s in bids],
        asks=[PriceLevel(price=Decimal(str(p)), size=Decimal(str(s))) for p, s in asks],
        timestamp=1700000000.0,
    )


def test_zero_slippage_top_of_book():
    book = _make_book(
        bids=[(3000, 10)],
        asks=[(3000, 10)],
    )
    # buying 5 when ask is 3000 -> vwap is 3000, mid is 3000, 0 bps slippage
    res = simulate_execution(book, side=OrderSide.BUY, amount=Decimal("5"), max_slippage_bps=Decimal("10"))
    assert res.vwap == Decimal("3000")
    assert res.slippage_bps == Decimal("0")
    assert not res.is_breach
    assert not res.partial_fill


def test_walk_multiple_ask_levels():
    book = _make_book(
        bids=[(2999, 10)],
        asks=[
            (3000, 2),  # cost 6000
            (3010, 3),  # cost 9030
            (3020, 5),  # cost 15100
        ],
    )
    # Buying 5 ETH: consumes 2 @ 3000 + 3 @ 3010 = 15030 total / 5 = 3006 vwap
    # Best ask = 3000, best bid = 2999 -> mid = 2999.5
    # slippage vs mid: (3006 - 2999.5) / 2999.5 * 10000 = 21.670278...
    res = simulate_execution(book, side=OrderSide.BUY, amount=Decimal("5"), max_slippage_bps=Decimal("20"))
    assert res.vwap == Decimal("3006")
    assert res.filled_amount == Decimal("5")
    assert res.slippage_bps > Decimal("21")
    assert res.is_breach is True


def test_walk_bids_sell_side():
    book = _make_book(
        bids=[
            (100, 10),
            (99, 10),
        ],
        asks=[(101, 10)],
    )
    # Sell 15 ETH: 10 @ 100 + 5 @ 99 = 1000 + 495 = 1495 / 15 = 99.6666...
    # mid = 100.5
    # slippage: (100.5 - 99.6666...) / 100.5 * 10000
    res = simulate_execution(book, side=OrderSide.SELL, amount=Decimal("15"), max_slippage_bps=Decimal("100"))
    assert not res.is_breach
    assert res.filled_amount == Decimal("15")
    assert res.vwap < Decimal("100")
