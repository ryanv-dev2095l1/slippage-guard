import pytest
from decimal import Decimal
from slippage_guard.types import OrderBook, PriceLevel, OrderSide
from slippage_guard.engine import simulate_execution, InsufficientLiquidityError


def _make_book(bids, asks) -> OrderBook:
    return OrderBook(
        symbol="BTC-USDT",
        exchange="okx",
        bids=[PriceLevel(price=Decimal(str(p)), size=Decimal(str(s))) for p, s in bids],
        asks=[PriceLevel(price=Decimal(str(p)), size=Decimal(str(s))) for p, s in asks],
        timestamp=1700000000.0,
    )


def test_exact_single_level_fill():
    book = _make_book(bids=[(50000, 1)], asks=[(50010, 1.5)])
    res = simulate_execution(book, side=OrderSide.BUY, amount=Decimal("1.5"), max_slippage_bps=Decimal("50"))
    assert res.filled_amount == Decimal("1.5")
    assert res.vwap == Decimal("50010")
    assert not res.partial_fill


def test_partial_fill_when_depth_exhausted_with_flag():
    book = _make_book(bids=[(50000, 1)], asks=[(50010, 1.0), (50020, 1.0)])
    # Request 3.0 BTC when only 2.0 available
    res = simulate_execution(
        book,
        side=OrderSide.BUY,
        amount=Decimal("3.0"),
        max_slippage_bps=Decimal("50"),
        allow_partial=True,
    )
    assert res.partial_fill is True
    assert res.filled_amount == Decimal("2.0")
    assert res.vwap == Decimal("50015")


def test_empty_book_raises():
    book = _make_book(bids=[], asks=[])
    with pytest.raises(InsufficientLiquidityError):
        simulate_execution(book, side=OrderSide.BUY, amount=Decimal("1.0"), max_slippage_bps=Decimal("10"))


def test_partial_fill_rejected_when_strict():
    book = _make_book(bids=[(50000, 0.5)], asks=[(50010, 0.5)])
    with pytest.raises(InsufficientLiquidityError):
        simulate_execution(
            book,
            side=OrderSide.BUY,
            amount=Decimal("2.0"),
            max_slippage_bps=Decimal("10"),
            allow_partial=False,
        )


def test_exact_tolerance_boundary():
    # mid is 100.0, best ask is 101.0 -> slippage = 100 bps exactly
    book = _make_book(bids=[(99.0, 10)], asks=[(101.0, 10)])
    res = simulate_execution(book, side=OrderSide.BUY, amount=Decimal("1.0"), max_slippage_bps=Decimal("100.0"))
    assert res.slippage_bps == Decimal("100")
    # <= max_slippage means within tolerance, not a breach
    assert not res.is_breach

    # 99.99 max tolerance -> breach
    res2 = simulate_execution(book, side=OrderSide.BUY, amount=Decimal("1.0"), max_slippage_bps=Decimal("99.99"))
    assert res2.is_breach is True
