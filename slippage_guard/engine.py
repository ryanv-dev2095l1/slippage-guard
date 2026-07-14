from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Optional
from slippage_guard.types import OrderBook, Side, SimulationResult, Benchmark


def walk_book(
    levels: List[Tuple[Decimal, Decimal]],
    target_amount: Decimal,
    is_quote_target: bool = False,
) -> Tuple[Decimal, Decimal, Decimal, bool]:
    filled_base = Decimal("0")
    filled_quote = Decimal("0")

    for price, size in levels:
        if size <= Decimal("0"):
            continue

        if is_quote_target:
            remaining_quote = target_amount - filled_quote
            level_quote = price * size
            if level_quote >= remaining_quote:
                take_base = remaining_quote / price
                filled_base += take_base
                filled_quote += remaining_quote
                vwap = filled_quote / filled_base
                return filled_base, filled_quote, vwap, True
            filled_base += size
            filled_quote += level_quote
        else:
            remaining_base = target_amount - filled_base
            if size >= remaining_base:
                filled_base += remaining_base
                filled_quote += remaining_base * price
                vwap = filled_quote / filled_base
                return filled_base, filled_quote, vwap, True
            filled_base += size
            filled_quote += size * price

    # ran out of levels before filling
    vwap = filled_quote / filled_base if filled_base > Decimal("0") else Decimal("0")
    return filled_base, filled_quote, vwap, False


def simulate(
    book: OrderBook,
    side: Side,
    amount: Decimal,
    tolerance_bps: int,
    quote_currency_target: bool = False,
    benchmark: Benchmark = Benchmark.TOP_OF_BOOK,
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

    if benchmark == Benchmark.MID_PRICE:
        if not book.bids or not book.asks:
            return SimulationResult(
                side=side,
                target_amount=amount,
                filled_base=Decimal("0"),
                filled_quote=Decimal("0"),
                vwap=Decimal("0"),
                ref_price=Decimal("0"),
                slippage_bps=0,
                aborted=True,
                reason="cannot calculate mid price with one-sided book",
            )
        ref_price = (book.bids[0][0] + book.asks[0][0]) / Decimal("2")
    else:
        ref_price = levels[0][0]

    # print(f"DEBUG: simulating {side} {amount} against {len(levels)} levels")
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
            ref_price=ref_price,
            slippage_bps=99999,
            aborted=True,
            reason=f"insufficient liquidity: only filled {filled_base} base out of {amount}",
        )

    if side == Side.BUY:
        diff = vwap - ref_price
    else:
        diff = ref_price - vwap

    # negative diff means better fill than benchmark (e.g. crossing below mid on sell)
    raw_bps = (diff / ref_price) * Decimal("10000")
    slippage_bps = int(raw_bps.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    should_abort = slippage_bps > tolerance_bps
    reason = None
    if should_abort:
        reason = f"slippage {slippage_bps}bps exceeds tolerance of {tolerance_bps}bps"

    return SimulationResult(
        side=side,
        target_amount=amount,
        filled_base=filled_base,
        filled_quote=filled_quote,
        vwap=vwap,
        ref_price=ref_price,
        slippage_bps=slippage_bps,
        aborted=should_abort,
        reason=reason,
    )
