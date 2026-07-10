from dataclasses import dataclass
from decimal import Decimal
from typing import List, Literal

Side = Literal["buy", "sell"]

@dataclass(frozen=True)
class Level:
    price: Decimal
    size: Decimal

@dataclass
class OrderBook:
    symbol: str
    bids: List[Level]
    asks: List[Level]
    timestamp_ms: int

    @property
    def mid_price(self) -> Decimal:
        if not self.bids or not self.asks:
            return Decimal("0")
        return (self.bids[0].price + self.asks[0].price) / Decimal("2")

@dataclass
class ExecutionResult:
    symbol: str
    side: Side
    requested_size: Decimal
    filled_size: Decimal
    vwap: Decimal
    mid_price: Decimal
    slippage_bps: Decimal
    worst_price: Decimal
    levels_consumed: int
    is_aborted: bool

class SlippageError(Exception):
    """Raised when calculated slippage crosses the user limit."""
    def __init__(self, symbol: str, actual_bps: Decimal, max_bps: Decimal):
        self.symbol = symbol
        self.actual_bps = actual_bps
        self.max_bps = max_bps
        super().__init__(f"{symbol} slippage {actual_bps:.2f} bps exceeds limit {max_bps:.2f} bps")

