from decimal import Decimal
from typing import List, Tuple, Optional
from slippage_guard.types import OrderBook, Side, SimulationResult


def walk_book(
    levels: List[Tuple[Decimal, Decimal]],
    target_amount: Decimal,
    is_quote_target: bool = False,
) -> Tuple[Decimal, Decimal, Decimal, bool]:
    filled_base = Decimal("0")
    filled_quote = Decimal("0")

    for price, size in levels:
        if is_quote_target:
            remaining_quote = target_amount - filled_quote
            level_quote = price * size
            if level_quote >= remaining_quote:
                take_base = remaining_quote / price
                filled_base += take_base
                filled_quote += remaining_quote
                return filled_base, filled_quote, filled_quote / filled_base, True
            filled_base += size
            filled_quote += level_quote
        else:
            remaining_base = target_amount - filled_base
            if size >= remaining_base:
                filled_base += remaining_base
                filled_quote += remaining_base * price
                return filled_base, filled_quote, filled_quote / filled_base, True
            filled_base += size
            filled_quote += size * price

    # ran out of levels before filling the whole size
    vwap = filled_quote / filled_base if filled_base > Decimal("0") else Decimal("0")
    return filled_base, filled_quote, vwap, False


def simulate(
    book: OrderBook,
    side: Side,
    amount: Decimal,
    tolerance_bps: int,
    quote_currency_target: bool = False,
) -> SimulationResult:
    """Simulate filling an order against L2 depth and check against max slippage."""
    levels = book.asks if side == Side.BUY else book.bids
    if not levels:
        return SimulationResult(
            side=side,
            target_amount=amount,
            filled_base=Decimal("0"),
            filled_quote=Decimal("0"),
            vwap=Decimal("0"),
            ref_price=Decimal("0"),
            slippage_bps=0,
            aborted=True,
            reason="order book side is completely empty",
        )

    best_price = levels[0][0]
    filled_base, filled_quote, vwap, complete = walk_book(
        levels, amount, is_quote_target=quote_currency_target
    )

    if not complete:
        return SimulationResult(
            side=side,
            target_amount=amount,
            filled_base=filled_base,
            filled_quote=filled_quote,
            vwap=vwap,
            ref_price=best_price,
            slippage_bps=9999,
            aborted=True,
            reason="insufficient book depth for order size",
        )

    if side == Side.BUY:
        diff = vwap - best_price
    else:
        diff = best_price - vwap

    # basis points relative to top of book
    slippage = (diff / best_price) * Decimal("10000")
    slippage_bps = int(slippage.quantize(Decimal("1")))

    should_abort = slippage_bps > tolerance_bps
    reason = None
    if should_abort:
        reason = f"slippage {slippage_bps}bps exceeds threshold {tolerance_bps}bps"

    return SimulationResult(
        side=side,
        target_amount=amount,
        filled_base=filled_base,
        filled_quote=filled_quote,
        vwap=vwap,
        ref_price=best_price,
        slippage_bps=slippage_bps,
        aborted=should_abort,
        reason=reason,
    )
