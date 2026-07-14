from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Literal, Optional

Side = Literal["buy", "sell", "BUY", "SELL"]

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
    exchange: str = "binance"

    @property
    def mid_price(self) -> Decimal:
        if not self.bids or not self.asks:
            return Decimal("0")
        return (self.bids[0].price + self.asks[0].price) / Decimal("2")

    @property
    def spread_bps(self) -> Decimal:
        if not self.bids or not self.asks:
            return Decimal("0")
        best_bid = self.bids[0].price
        best_ask = self.asks[0].price
        mid = self.mid_price
        if mid == Decimal("0"):
            return Decimal("0")
        return ((best_ask - best_bid) / mid) * Decimal("10000")

@dataclass
class RebalanceLeg:
    symbol: str
    side: str
    amount: Decimal
    # if quote_currency is true, amount is USD/USDT rather than base asset
    quote_currency: bool = False
    max_slippage_bps: Optional[Decimal] = None

@dataclass
class ExecutionResult:
    symbol: str
    side: str
    requested_size: Decimal
    filled_size: Decimal
    vwap: Decimal
    mid_price: Decimal
    slippage_bps: Decimal
    worst_price: Decimal
    levels_consumed: int
    is_aborted: bool
    fees_estimated: Decimal = Decimal("0")
    details: Dict[str, str] = field(default_factory=dict)

@dataclass
class BatchSimulationResult:
    passed: bool
    total_legs: int
    aborted_legs: int
    results: List[ExecutionResult]
    summary_reason: Optional[str] = None

class SlippageError(Exception):
    """Raised when calculated slippage crosses the user limit."""
    def __init__(self, symbol: str, actual_bps: Decimal, max_bps: Decimal):
        self.symbol = symbol
        self.actual_bps = actual_bps
        self.max_bps = max_bps
        super().__init__(f"{symbol} slippage {actual_bps:.2f} bps exceeds limit {max_bps:.2f} bps")

class InsufficientLiquidityError(Exception):
    pass

class OrderBookFetchError(Exception):
    pass
